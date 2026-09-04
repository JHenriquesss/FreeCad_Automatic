# ============================================================================
# estrutura_casa.py - ESTRUTURA DA CASA RESIDENCIAL (terrea ou sobrado)
#
# A casa do Project Loop tinha instalacoes e NAO tinha estrutura: o adaptador
# declarava arquitetura + eletrico + hidraulica e o escopo dizia
# `estrutura: not_available`. Nenhuma laje, nenhuma viga, nenhum pilar, nenhuma
# fundacao - a carga da casa nunca chegava ao chao. Os modulos de calculo ja
# existiam e ja estavam aferidos (laje_concreto no Ex.1 Cap.7 de Carvalho,
# viga_concreto/viga_baldrame, pilar_concreto em Bastos, fundacao_sapata contra
# Alonso). Este modulo LIGA os dois lados; nao inventa metodo novo.
#
#     carga de uso (NBR 6120 Tab.10)
#          -> pavimento-tipo (laje -> viga continua -> pilar)
#          -> descida de cargas com alpha_n (6.12)
#          -> pilares continuos (secao adotada lance a lance)
#          -> VIGA BALDRAME sob a alvenaria terrea
#          -> fundacao (sapata/bloco/estaca, pela sondagem declarada)
#
# POR QUE E' MAIS CURTA QUE A DO EDIFICIO (G3). Sao os MESMOS modulos, sem a
# camada de estabilidade horizontal: nao ha gamma_z, nao ha desaprumo e nao ha
# ELS de deslocamento lateral. Isso NAO e' uma dispensa que este modulo concede
# - e' uma FRONTEIRA, e ela tem guarda: mais de %d pavimentos e a entrada e'
# RECUSADA com o nome da tipologia certa (edificio-multipavimento), em vez de um
# predio de cinco andares atravessar a casa sem que ninguem verifique a
# estabilidade global. `acao_horizontal` sai no escopo como not_available.
#
# O QUE A CASA TEM E O EDIFICIO NAO TINHA - A VIGA BALDRAME. O G3 publica
# `viga_baldrame: not_available` porque num predio a alvenaria do terreo sobe
# sobre a estrutura ja modelada. Numa casa e' o contrario: a alvenaria terrea
# nasce no baldrame e desce direto para a sapata, POR FORA da descida de cargas
# (que so acumula o que as lajes entregam aos pilares). Se o baldrame nao
# existisse, o peso de todas as paredes do terreo simplesmente sumiria entre o
# pavimento e a fundacao - a saturacao silenciosa na sua forma mais cara. Por
# isso a reacao do baldrame e' SOMADA ao N_base de cada pilar antes de a
# fundacao ser dimensionada, e um gate de FECHAMENTO confere que a soma das
# reacoes reproduz o peso lancado.
#
# A VIGA E' VERIFICADA, NAO SO ANALISADA. `pavimento_tipo` monta a viga continua
# e devolve a envoltoria de esforcos (14.6.6), mas nada ali confere se a secao
# declarada RESISTE. Aqui cada tramo passa por `viga_concreto.verifica_viga` com
# o M_d e o V_d da envoltoria: flexao, cortante, flecha (Tab.13.3) e fissuracao.
# Uma viga que nao cabe reprova com o tramo nomeado.
#
# Unidades: m, kN ; fck/fyk em kN/m2. STATELESS.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Estrutura da casa residencial: pavimento, descida, pilares, baldrame e
fundacao, sem a camada de estabilidade horizontal do edificio."""

from __future__ import annotations

import copy
import os

import cargas_nbr6120 as cg
import descida_cargas as dc
import fundacao_edificio as fe
import laje_concreto as lj
import pavimento_tipo as pt
import pilar_continuo as pcn
import viga_baldrame as vb
import viga_concreto as vgc
import viga_continua as vc

GAMMA_C_CONC = 25.0        # peso especifico do concreto armado (kN/m3), NBR 6120
GF = 1.4                   # ponderacao das acoes (ELU, combinacao normal)

# Teto de pavimentos desta tipologia. Casa terrea (1) e sobrado (2) sao o que a
# cadeia SEM estabilidade horizontal cobre; ver a nota do cabecalho.
MAX_PAVIMENTOS = 2

# teto de iteracoes do ponto fixo espessura-da-laje x carga (ver `rodar`)
MAX_ITER_LAJE = 6

# Secoes de pilar tentadas numa CASA, da menor para a maior (b, h) em m. A lista
# do edificio comeca em 19 x 30; a casa usa o pilar de 14 cm, que e' o minimo
# absoluto de 13.2.3 (com o gamma_n de 13.2.3 majorando os esforcos, aplicado
# por `pilar_concreto`). Ac >= 360 cm2 tambem e' exigencia de 13.2.3 e por isso
# nao ha 14 x 14 na lista.
SECOES_PILAR_CASA = ((0.14, 0.30), (0.19, 0.30), (0.19, 0.40), (0.20, 0.50),
                     (0.25, 0.50), (0.30, 0.60))

# Onde corre a viga baldrame. 'contorno' e' a mesma convencao que
# `pavimento_tipo` usa para `parede_sobre_vigas`: a alvenaria de fechamento fica
# nas linhas de contorno. 'todas' inclui as linhas internas (paredes internas
# assentes em baldrame). Nao ha default de PAREDE: sem `baldrame` declarado o
# baldrame nao existe e o aviso diz o que ficou de fora.
LINHAS_BALDRAME = ("contorno", "todas")

# tolerancia do fechamento de carga do baldrame (fracao)
TOL_FECHAMENTO = 0.02


class EntradaEstrutura(ValueError):
    """A entrada declarada nao descreve uma casa que esta cadeia possa calcular."""


def _eixos(vaos):
    """Coordenadas (m) das linhas de eixo a partir da lista de vaos."""
    xs = [0.0]
    for v in vaos:
        xs.append(xs[-1] + float(v))
    return xs


def _carga_escada_por_pavimento(r_escada, cfg_escada):
    """Reacao caracteristica da escada, POR pavimento, separada em g e q (kN).

    G42 (gemeo do G38 na casa): a escada era dimensionada DEPOIS da descida e
    o seu peso jamais chegava a pilar nenhum - carga que some, com todos os
    gates dizendo OK. A escada agora e' dimensionada ANTES da descida e a sua
    reacao realimenta os lances, no mesmo remedio do edificio.

    Hipoteses EXPLICITAS (nada arbitrado em silencio):
      - a escada declarada repete-se em cada pavimento: o peso que desce por
        nivel e' o de UM lance como dimensionado, vezes 'n_lances_por_pavimento'
        (default 1);
      - a reacao total do lance (W = (g+q).L.largura) e' dividida entre os
        'apoios' declarados (nomes de pilares); sem 'apoios', divide-se
        uniformemente entre TODOS os pilares e isso fica registrado em
        'distribuicao';
      - SEM 'largura' nao ha como calcular W: a carga e' INDEFINIDA, nao zero.
        Nesse caso devolve 'erro' e quem chama REPROVA o fechamento em vez de
        seguir com pilares mais leves (fail-closed);
      - o q da escada so recebe o alpha_n de 6.12 se o uso for REDUTIVEL pela
        Tabela 10; q explicito ('informado explicitamente') nao reduz."""
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


# ---------------------------------------------------------------------------
# VIGAS: verificacao da secao contra a envoltoria da viga continua
# ---------------------------------------------------------------------------
def verifica_vigas(pav, fck, fyk, com_alvenaria):
    """Verifica CADA TRAMO de CADA linha de viga do pavimento.

    `pavimento_tipo` entrega a envoltoria de esforcos (14.6.6) mas nao confere a
    secao. Aqui o M_d e o V_d da envoltoria vao para `viga_concreto`, que faz
    flexao (17.2.2), cortante (17.4.2), flecha (Tab.13.3) e fissuracao.

    MOMENTO NEGATIVO - a costura que nao pode ficar solta. Sozinho,
    `verifica_viga` dimensiona a face superior por w*L^2/10 (coeficiente de
    tabela); num apoio interno de dois vaos o momento real e' w*L^2/8, e a
    armadura superior sairia ABAIXO do esforco sem que nenhum gate reclamasse.
    Aqui o M- da envoltoria e' passado explicitamente (`M_d_neg`), e o registro
    publica lado a lado o que a analise pediu e o que foi dimensionado: se um
    dia o repasse se perder, `momento_negativo_coberto` cai e o tramo REPROVA,
    em vez de voltar em silencio ao coeficiente menor.

    Devolve {'OK', 'por_linha', 'reprovados', 'n_tramos'}.
    """
    linhas = []
    reprovados = []
    n_tramos = 0
    for linha in list(pav["vigas_x"]) + list(pav["vigas_y"]):
        b, h = float(linha["b"]), float(linha["h"])
        w_self = GAMMA_C_CONC * b * h
        continua = "continua" if linha["n_tramos"] > 1 else "simples"
        tramos = []
        for k, L in enumerate(linha["vaos"]):
            n_tramos += 1
            # `verifica_viga` soma o peso proprio por dentro; a carga do tramo
            # que vem do pavimento JA o inclui (pavimento_tipo somou peso_viga).
            # Descontar aqui e' o que impede o peso proprio de entrar duas vezes.
            q_tramo = (float(linha["g_tramos"][k]) + float(linha["q_tramos"][k])
                       - w_self)
            # o M+ arma a face INFERIOR e o M- a SUPERIOR; sao dois
            # dimensionamentos distintos, nao a envoltoria dos dois num numero so
            M_pos_env = abs(float(linha["M_positivo"][k]))
            M_neg_env = max(abs(float(linha["M_apoios"][k])),
                            abs(float(linha["M_apoios"][k + 1])))
            r = vgc.verifica_viga({
                "vao": L, "b": b, "h": h, "fck": fck, "fyk": fyk,
                "q": max(q_tramo, 0.0),
                "continuidade": continua,
                "M_d": GF * M_pos_env, "V_d": GF * abs(float(linha["V_max"][k])),
                "M_d_neg": GF * M_neg_env,
                # ELS-W: o momento de SERVICO e' o da analise (caracteristico),
                # nao o w*L2/10 de tabela que o modulo usaria por default
                "M_serv": M_pos_env,
                # a viga de contorno recebe a alvenaria de fechamento (a carga
                # ja esta em g_tramos): o limite de flecha passa a ser o de
                # 13.3 para parede - L/500 ou 10 mm depois de a parede subir -
                # e nao o L/250 visual. `q_alvenaria` fica ZERO justamente
                # porque a parede ja esta na carga; declara-la de novo seria
                # conta-la duas vezes no ELS.
                "suporta_alvenaria": bool(com_alvenaria and linha["contorno"]),
                "q_alvenaria": 0.0})
            # `M_d_neg` volta ARREDONDADO a 2 casas; a folga de 0,01 kN.m
            # e' o arredondamento, nao tolerancia de projeto
            M_d_neg_coberto = GF * M_neg_env <= float(r["M_d_neg"]) + 0.01
            ok = bool(r["OK"]) and (M_d_neg_coberto if continua == "continua"
                                    else True)
            registro = {
                "tramo": k + 1, "L": L, "OK": ok,
                "M_d_kNm": r["M_d"], "V_d_kN": r["V_d"],
                "M_d_neg_dimensionado_kNm": r["M_d_neg"],
                "M_d_neg_envoltoria_kNm": round(GF * M_neg_env, 2),
                "momento_negativo_coberto": M_d_neg_coberto,
                "As_inf_cm2": r["As_inf_cm2"], "As_sup_cm2": r["As_sup_cm2"],
                "els": r["els"], "cort_ok": r["cort_ok"],
                "fissu_ok": r["fissu_ok"], "sec_ok": r["sec_ok"],
                "verificacao": r}
            if not ok:
                motivos = []
                if not r["sec_ok"] or not r["ok_dominio"]:
                    motivos.append("secao insuficiente a flexao positiva")
                if not r["sec_ok_neg"] or not r["ok_dominio_neg"]:
                    # sem esta linha, um tramo reprovado SO pelo momento negativo
                    # sairia com a lista de motivos vazia - reprovado sem dizer
                    # por que, que e' quase tao ruim quanto aprovado em silencio
                    motivos.append("secao insuficiente ao momento negativo")
                if not r["cort_ok"]:
                    motivos.append("cortante")
                if not r["els_ok"]:
                    motivos.append("flecha (%s)" % r["els"]["criterio"])
                if not r["fissu_ok"]:
                    motivos.append("abertura de fissuras")
                if not M_d_neg_coberto:
                    motivos.append(
                        "momento negativo da envoltoria (%.2f kN.m) maior que o "
                        "dimensionado por w.L2/10 (%.2f kN.m)"
                        % (GF * M_neg_env, r["M_d_neg"]))
                registro["motivos"] = motivos
                reprovados.append("%s tramo %d: %s"
                                  % (linha["nome"], k + 1, "; ".join(motivos)))
            tramos.append(registro)
        linhas.append({"nome": linha["nome"], "b": b, "h": h,
                       "contorno": bool(linha["contorno"]),
                       "OK": all(t["OK"] for t in tramos), "tramos": tramos})
    return {"OK": not reprovados, "por_linha": linhas,
            "reprovados": reprovados, "n_tramos": n_tramos}


# ---------------------------------------------------------------------------
# VIGA BALDRAME: a alvenaria terrea que nao passa pela descida de cargas
# ---------------------------------------------------------------------------
def linhas_de_baldrame(vaos_x, vaos_y, modo):
    """Linhas da malha que recebem baldrame, no formato (nome, eixo, indice, vaos).

    'contorno': as quatro linhas do perimetro (a mesma convencao de
    `parede_sobre_vigas`). 'todas': todas as linhas da malha.
    """
    if modo not in LINHAS_BALDRAME:
        raise EntradaEstrutura(
            "baldrame.linhas invalido: %r (use %s)"
            % (modo, " ou ".join(LINHAS_BALDRAME)))
    nx, ny = len(vaos_x), len(vaos_y)
    linhas = []
    for j in range(ny + 1):
        if modo == "todas" or j in (0, ny):
            linhas.append(("BX-%d" % j, "x", j, list(vaos_x)))
    for i in range(nx + 1):
        if modo == "todas" or i in (0, nx):
            linhas.append(("BY-%d" % i, "y", i, list(vaos_y)))
    return linhas


def dimensiona_baldrame(cfg, vaos_x, vaos_y, fck, fyk):
    """Dimensiona a viga baldrame e reparte as reacoes pelos pilares.

    cfg: {'b','h' (m), 'parede' {tipo, espessura_cm, revestimento_cm, altura},
          'q_parede' (kN/m, alternativa a 'parede'), 'linhas', 'continuidade'}.

    UMA SECAO PARA A OBRA, dimensionada no MAIOR vao: e' a pratica corrente e e'
    o lado conservador. `viga_baldrame.dimensiona_baldrame` ADOTA a altura (ela
    cresce se a declarada nao atende a flecha sob alvenaria), e e' a altura
    ADOTADA que pesa nas reacoes - senao a fundacao receberia o peso proprio de
    um baldrame que nao vai ser construido.

    As REACOES saem da analise de viga continua (`viga_continua`), nao de area
    de influencia: num baldrame de varios tramos o apoio interno recebe mais que
    metade de cada vao vizinho, e a repartir por metades a sapata do meio sairia
    leve.

    Devolve {'OK', 'secao', 'verificacao', 'por_pilar', 'fechamento', ...}.
    """
    import cargas_nbr6120 as cg

    b = float(cfg.get("b", 0.15))
    h0 = float(cfg.get("h", 0.40))
    modo = cfg.get("linhas", "contorno")
    linhas = linhas_de_baldrame(vaos_x, vaos_y, modo)
    if not linhas:
        raise EntradaEstrutura("nenhuma linha de baldrame na malha declarada")

    parede = cfg.get("parede")
    if parede is not None:
        if not isinstance(parede, dict):
            raise EntradaEstrutura("baldrame.parede deve ser um objeto")
        try:
            q_parede = cg.carga_linear_parede(
                parede["tipo"], parede["espessura_cm"], parede["altura"],
                parede.get("revestimento_cm", 1.0))
        except KeyError as exc:
            raise EntradaEstrutura(
                "baldrame.parede precisa de 'tipo', 'espessura_cm' e 'altura' "
                "(Tabela 2 da NBR 6120): %s" % exc) from exc
        proveniencia = ("Tabela 2 da NBR 6120: %s e=%s cm, h=%.2f m"
                        % (parede["tipo"], parede["espessura_cm"],
                           float(parede["altura"])))
    elif cfg.get("q_parede") is not None:
        q_parede = float(cfg["q_parede"])
        proveniencia = "declarada no spec (baldrame.q_parede)"
    else:
        raise EntradaEstrutura(
            "o baldrame precisa da alvenaria que ele carrega: declare "
            "baldrame.parede (tipo/espessura_cm/altura, Tabela 2 da NBR 6120) "
            "ou baldrame.q_parede em kN/m. Um baldrame que so carrega o proprio "
            "peso nao e' o baldrame desta casa")
    if q_parede < 0:
        raise EntradaEstrutura("a carga de parede do baldrame nao pode ser < 0")

    vao_critico = max(max(l[3]) for l in linhas)
    n_max = max(len(l[3]) for l in linhas)
    continuidade = cfg.get("continuidade",
                           "continua" if n_max > 1 else "simples")
    r = vb.dimensiona_baldrame({
        "vao": vao_critico, "b": b, "h": h0, "fck": fck, "fyk": fyk,
        "q_parede": q_parede, "continuidade": continuidade,
        "cobrimento": cfg.get("cobrimento", 0.05)})
    h = float(r["h"])
    w = q_parede + GAMMA_C_CONC * b * h          # carga caracteristica (kN/m)

    por_pilar = {}
    por_linha = []
    for nome, eixo, indice, vaos in linhas:
        analise = vc.analisa({
            "tramos": [{"L": L, "b": b, "h": h} for L in vaos],
            "g": [w] * len(vaos), "q": [0.0] * len(vaos), "fck": fck})
        reacoes = analise["reacoes"]
        for k, reacao in enumerate(reacoes):
            i, j = (k, indice) if eixo == "x" else (indice, k)
            chave = "P%d%d" % (i + 1, j + 1)
            por_pilar[chave] = round(por_pilar.get(chave, 0.0) + float(reacao), 3)
        por_linha.append({"nome": nome, "eixo": eixo, "indice": indice,
                          "vaos": list(vaos),
                          "reacoes_kN": [round(float(v), 3) for v in reacoes],
                          "M_positivo": list(analise["M_positivo"]),
                          "M_apoios": list(analise["M_apoios"])})

    # FECHAMENTO: o que desce pelos pilares tem de ser o que foi lancado nas
    # linhas. E' a mesma conta de `pavimento_tipo.verifica_fechamento` e serve ao
    # mesmo proposito - uma linha cujo baldrame nao foi lancado em pilar nenhum
    # simplesmente some, e a casa fica mais leve sem nenhum gate reclamar.
    comprimento = sum(sum(l[3]) for l in linhas)
    esperado = w * comprimento
    somado = sum(por_pilar.values())
    erro_rel = abs(somado - esperado) / esperado if esperado > 0 else 0.0
    fechamento = {"ok": erro_rel <= TOL_FECHAMENTO,
                  "N_pilares_kN": round(somado, 2),
                  "carga_esperada_kN": round(esperado, 2),
                  "erro_rel": round(erro_rel, 5),
                  "comprimento_m": round(comprimento, 3)}
    return {
        "OK": bool(r["OK"]) and fechamento["ok"],
        "secao": {"b": b, "h": h, "h_declarada": h0},
        "adotou_altura_maior": h > h0 + 1e-9,
        "continuidade": continuidade,
        "vao_critico_m": vao_critico,
        "q_parede_kN_m": round(q_parede, 3),
        "proveniencia_parede": proveniencia,
        "w_kN_m": round(w, 3),
        "linhas": modo, "por_linha": por_linha, "por_pilar": por_pilar,
        "fechamento": fechamento, "verificacao": r,
    }


# ---------------------------------------------------------------------------
# ORQUESTRADOR
# ---------------------------------------------------------------------------
def _valida(spec):
    """Recusa a entrada que esta cadeia nao pode calcular, com o motivo."""
    geo = spec.get("geometria")
    if not isinstance(geo, dict):
        raise EntradaEstrutura("geometria deve ser um objeto com vaos_x, vaos_y "
                               "e pe_direito")
    for eixo in ("vaos_x", "vaos_y"):
        vaos = geo.get(eixo)
        if not isinstance(vaos, (list, tuple)) or not vaos:
            raise EntradaEstrutura("geometria.%s deve ser uma lista nao vazia "
                                   "de vaos" % eixo)
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                   and v > 0 for v in vaos):
            raise EntradaEstrutura("todo vao de %s deve ser numerico > 0" % eixo)
    if not (isinstance(geo.get("pe_direito"), (int, float))
            and not isinstance(geo["pe_direito"], bool) and geo["pe_direito"] > 0):
        raise EntradaEstrutura("geometria.pe_direito deve ser > 0")
    pavimentos = spec.get("pavimentos")
    if not isinstance(pavimentos, list) or not pavimentos:
        raise EntradaEstrutura("pavimentos deve ser uma lista nao vazia, do topo "
                               "para a base")
    for i, pv in enumerate(pavimentos):
        if not isinstance(pv, dict) or not pv.get("nome") or not pv.get("uso"):
            raise EntradaEstrutura("pavimentos[%d] precisa de 'nome' e 'uso' "
                                   "(chave da Tabela 10 da NBR 6120)" % i)
    if len(pavimentos) > MAX_PAVIMENTOS:
        # A fronteira do cabecalho, com guarda. Deixar passar seria entregar um
        # predio calculado SEM gamma_z, sem desaprumo e sem ELS lateral, com
        # todos os gates dizendo ATENDE.
        raise EntradaEstrutura(
            "esta cadeia cobre casa terrea ou sobrado (ate %d pavimentos) e "
            "recebeu %d: sem estabilidade horizontal (gamma_z, desaprumo, ELS "
            "de deslocamento lateral) o resultado nao descreveria a estrutura. "
            "Use a tipologia 'edificio' (edificio_multipavimento), que a calcula"
            % (MAX_PAVIMENTOS, len(pavimentos)))
    materiais = spec.get("materiais")
    if not isinstance(materiais, dict):
        raise EntradaEstrutura("materiais deve declarar fck e fyk (kN/m2)")
    for chave in ("fck", "fyk"):
        valor = materiais.get(chave)
        if not (isinstance(valor, (int, float)) and not isinstance(valor, bool)
                and valor > 0):
            raise EntradaEstrutura("materiais.%s deve ser numerico > 0" % chave)


def rodar(spec):
    """Dimensiona a estrutura da casa e devolve os gates.

    spec: {
      'geometria' : {'vaos_x': [...], 'vaos_y': [...], 'pe_direito': m};
      'pavimentos': lista do TOPO para a BASE (1 = terrea, 2 = sobrado), cada um
                    {'nome', 'uso'} (chave da Tabela 10 da NBR 6120);
      'laje'      : {'h': m, 'revestimento_kN_m2': opc};
      'viga'      : {'b','h'} (m);
      'materiais' : {'fck','fyk'} (kN/m2);
      'parede_sobre_vigas'   : opc, alvenaria SOBRE as vigas do pavimento;
      'parede_sem_posicao_pp': opc (kN/m), Tabela 11;
      'baldrame'  : opc - a alvenaria TERREA, que desce por fora da descida de
                    cargas. Sem ele o peso das paredes do terreo NAO entra na
                    fundacao, e o aviso diz isso;
      'fundacao'  : opc, sub-spec de fundacao_edificio.dimensiona (perfil_spt
                    e/ou sigma_solo_adm). SEM ele nao ha fundacao - a tensao do
                    solo nunca e' arbitrada;
      'escada'    : opc, sub-spec de escada_concreto.dimensiona (sobrado) +
                    chaves proprias: 'largura' OBRIGATORIA para a descida (sem
                    ela a reacao e' indefinida e o fechamento REPROVA);
                    'apoios' opc, lista de pilares que recebem a escada (sem
                    ele, distribuicao uniforme); 'n_lances_por_pavimento' opc,
                    default 1;
      'out_dir'   : opc - se dado, escreve a planta de formas (SVG).
    }

    O retorno usa as MESMAS chaves do edificio multipavimento ('pavimento',
    'descida', 'pilares', 'laje', 'fundacao') porque e' esse o contrato que
    `bim_edificio` le para emitir o modelo neutro e o IFC4. Uma casa e um predio
    de concreto sao a mesma geometria com alturas diferentes; duplicar o emissor
    seria criar a segunda descricao que envelhece.
    """
    _valida(spec)
    geo = spec["geometria"]
    mat = spec["materiais"]
    laje = spec.get("laje", {})
    viga = spec.get("viga", {})
    fck, fyk = mat["fck"], mat["fyk"]

    def _tipo_para(uso, h_laje):
        d = {"vaos_x": geo["vaos_x"], "vaos_y": geo["vaos_y"],
             "h_laje": h_laje,
             "revestimento_kN_m2": laje.get("revestimento_kN_m2", 1.0),
             "uso": uso,
             "b_viga": viga.get("b", 0.15), "h_viga": viga.get("h", 0.40),
             "fck": fck, "fyk": fyk, "pe_direito": geo["pe_direito"]}
        if spec.get("parede_sobre_vigas"):
            d["parede_sobre_vigas"] = spec["parede_sobre_vigas"]
        if spec.get("parede_sem_posicao_pp"):
            d["parede_sem_posicao_pp"] = spec["parede_sem_posicao_pp"]
        return d

    # ------------------------------ PAVIMENTO + LAJE (ponto fixo na espessura)
    # `dimensiona_laje` ADOTA a menor espessura que atende, que pode ser MAIOR
    # que a declarada. Se a cadeia seguisse com a declarada, vigas, pilares,
    # baldrame e fundacao seriam dimensionados para o peso proprio de uma laje
    # que nao e' a que vai ser construida - 25 kN/m3 x delta_h de carga
    # permanente a menos, com todos os gates dizendo OK. A espessura adotada
    # REALIMENTA a carga ate parar de crescer.
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
    # G42 (gemeo do G38): a escada e' dimensionada ANTES da descida porque a
    # sua reacao REALIMENTA os lances. Antes ela era calculada depois (a reacao
    # so existia la embaixo) e o peso dela jamais descia para pilar nenhum:
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
        e.setdefault("desnivel", geo["pe_direito"])
        r_escada = ec.dimensiona(e)
        stair = _carga_escada_por_pavimento(r_escada, spec["escada"])
        if stair.get("erro"):
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
    for nome in sorted(desc["pilares"]):
        lances = dc.lances_para_pilar(desc, nome)
        escolhidos, erros = pcn.dimensiona_pilar_continuo(
            lances, fck, fyk, secoes=SECOES_PILAR_CASA)
        r = pcn.dimensiona({"lances": escolhidos, "fck": fck, "fyk": fyk})
        if erros:
            r = dict(r, OK=False)
            r["erros"] = list(r["erros"]) + erros
        pilares[nome] = r
        if not r["OK"]:
            erros_pilar.append(nome)

    # ---------------------------------------------------------------- VIGAS
    r_vigas = verifica_vigas(pav, fck, fyk,
                            com_alvenaria=pav["g_parede_kN_m"] > 0)

    # ------------------------------------------------------------- BALDRAME
    baldrame = None
    erro_baldrame = None
    if spec.get("baldrame"):
        try:
            baldrame = dimensiona_baldrame(spec["baldrame"], geo["vaos_x"],
                                           geo["vaos_y"], fck, fyk)
        except EntradaEstrutura as exc:
            erro_baldrame = str(exc)

    # --------------------------------------------------------------- ESCADA
    # (dimensionada ANTES da descida, em G42 - ver bloco acima)
    # --------------------------------------------------------------- PLANTA
    planta = None
    if spec.get("out_dir"):
        import desenho_pavimento as dp
        os.makedirs(spec["out_dir"], exist_ok=True)
        planta = dp.gerar_planta_formas(
            pav, os.path.join(spec["out_dir"], "planta-formas-casa.svg"),
            descida=desc, titulo="PLANTA DE FORMAS - CASA RESIDENCIAL")

    # ------------------------------------------------------------- FUNDACAO
    # A carga que chega a sapata e' a que desceu pelo pilar MAIS a reacao do
    # baldrame - a alvenaria terrea nao passa por pilar nenhum. Somar aqui, e
    # nao antes, e' o correto: o baldrame entrega no TOPO da fundacao, abaixo do
    # ultimo lance, e nao carrega o pilar.
    fundacao = None
    erro_fundacao = None
    reacoes_baldrame = (baldrame or {}).get("por_pilar") or {}
    if fe.declarada(spec.get("fundacao")):
        pilares_fund = []
        for nome in sorted(desc["pilares"]):
            registro = next(x for x in pav["pilares"] if x["nome"] == nome)
            lance_base = pilares[nome]["lances"][-1]
            pilares_fund.append({
                "nome": nome, "i": registro["i"], "j": registro["j"],
                "posicao": registro["posicao"],
                "N_base_k": (desc["pilares"][nome]["N_base_k"]
                             + float(reacoes_baldrame.get(nome, 0.0))),
                "secao": (lance_base["b"], lance_base["h"]),
            })
        try:
            fundacao = fe.dimensiona(spec["fundacao"], {
                "pilares": pilares_fund,
                "eixos_x": _eixos(geo["vaos_x"]),
                "eixos_y": _eixos(geo["vaos_y"]),
                "materiais": {"fck": fck, "fyk": fyk},
                "estabilidade": None})
        except fe.EntradaFundacao as exc:
            erro_fundacao = str(exc)

    # ---------------- FECHAMENTO DA CASA CONTRA A CARGA DECLARADA (G42)
    # O gate antigo fechava o total DO QUE FOI INCLUIDO: `verifica_fechamento`
    # confere UM pavimento-tipo contra a sua propria carga, entao a escada -
    # que nunca entrava nem no pavimento nem na descida - era invisivel por
    # construcao (irmao do G38 no edificio). O fechamento agora confere a BASE
    # DA DESCIDA (bruta, sem reducao de 6.12) contra a carga DECLARADA: a soma
    # dos N_total_k de cada pavimento MAIS o peso bruto total da escada. Se a
    # escada foi declarada sem largura (reacao indefinida), o fechamento
    # REPROVA em vez de fechar sem ela.
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
    fechamento_ok = bool(fech["ok"] and erro_total <= TOL_FECHAMENTO
                         and escada_erro is None)

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
        "laje": {"OK": bool(r_laje.get("OK")), "h_cm": r_laje.get("h", 0) * 100},
        # a carga que desceu foi calculada com a espessura que a laje ADOTOU
        "laje_compatibilizada": {
            "OK": convergiu and abs(pav["h_laje_usada"] - r_laje["h"]) <= 1e-9,
            "h_declarada_cm": h_declarada * 100,
            "h_adotada_cm": r_laje["h"] * 100,
            "h_na_carga_cm": pav["h_laje_usada"] * 100,
            "iteracoes": iteracoes},
        # ao contrario do edificio, aqui a viga e' VERIFICADA (nao so analisada)
        "vigas": {"OK": r_vigas["OK"], "n_linhas": len(r_vigas["por_linha"]),
                  "n_tramos": r_vigas["n_tramos"],
                  "reprovadas": list(r_vigas["reprovados"])},
        "pilares": {"OK": not erros_pilar, "reprovados": erros_pilar,
                    "n": len(pilares)},
    }
    if baldrame is not None:
        gates["viga_baldrame"] = {
            "OK": baldrame["OK"],
            "b_cm": baldrame["secao"]["b"] * 100,
            "h_cm": baldrame["secao"]["h"] * 100,
            "q_parede_kN_m": baldrame["q_parede_kN_m"],
            "fechamento_OK": baldrame["fechamento"]["ok"],
            "erro_rel": baldrame["fechamento"]["erro_rel"]}
    elif erro_baldrame is not None:
        gates["viga_baldrame"] = {"OK": False, "erro": erro_baldrame}
    if fundacao is not None:
        gates["fundacao"] = dict(fundacao["gate"])
    elif erro_fundacao is not None:
        gates["fundacao"] = {"OK": False, "erro": erro_fundacao}
    if r_escada is not None:
        gates["escada"] = {
            "OK": bool(r_escada["OK"]) and escada_erro is None,
            "desceu_aos_pilares": detalhe_escada is not None,
            "W_g_por_pav_kN": (stair["W_g"] if stair is not None else None),
            "W_q_por_pav_kN": (stair["W_q"] if stair is not None else None),
            "distribuicao": (detalhe_escada["distribuicao"]
                             if detalhe_escada else None),
            "erro": escada_erro}

    reprovados = [k for k, g in gates.items() if not g["OK"]]
    N_base = {nome: round(desc["pilares"][nome]["N_base_k"]
                          + float(reacoes_baldrame.get(nome, 0.0)), 2)
              for nome in desc["pilares"]}
    return {
        "ATENDE": not reprovados, "reprovados": reprovados, "gates": gates,
        "pavimento": pav, "descida": desc, "pilares": pilares,
        "laje": r_laje, "vigas": r_vigas, "baldrame": baldrame,
        "baldrame_erro": erro_baldrame,
        "escada": r_escada, "escada_descida": detalhe_escada,
        "escada_erro": escada_erro, "planta": planta,
        "fundacao": fundacao, "fundacao_erro": erro_fundacao,
        "n_pavimentos": len(pavs),
        "tipologia": "terrea" if len(pavs) == 1 else "sobrado",
        "H_total_m": len(pavs) * geo["pe_direito"],
        "h_laje_adotada": r_laje["h"], "h_laje_declarada": h_declarada,
        # N_fundacao = o que desceu pelo pilar + o que o baldrame entregou
        "N_fundacao_k": N_base,
        "N_base_max_k": max(N_base.values()),
        "reacoes_baldrame_k": copy.deepcopy(reacoes_baldrame),
        "registro_6120": desc["registro_6120"],
        "escopo": escopo(baldrame is not None, fundacao is not None),
    }


def escopo(com_baldrame, com_fundacao):
    """O que esta cadeia cobre e o que ela deixa de fora, dito em voz alta."""
    return {
        "laje": "implemented",
        "viga": "implemented",
        "pilar": "implemented",
        "viga_baldrame": "implemented" if com_baldrame else "not_available",
        "fundacao": "implemented" if com_fundacao else "not_available",
        # a fronteira do cabecalho: casa terrea/sobrado nao roda estabilidade
        # global neste framework. Nomeada, com guarda de entrada.
        "acao_horizontal": "not_available",
        "estabilidade_global": "not_available",
        "desaprumo": "not_available",
        "alvenaria_estrutural": "not_available",
        "telhado_madeira": "not_available",
        "aprovacao_legal": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def relatorio_pt(r):
    """Quadro-resumo da estrutura da casa."""
    pav = r["pavimento"]
    g = r["gates"]
    L = ["ESTRUTURA DA CASA RESIDENCIAL (%s) - quadro-resumo" % r["tipologia"].upper(),
         "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
         "  %d pavimento(s) ; malha %d x %d vaos ; %.1f m2 por pavimento"
         % (r["n_pavimentos"], len(pav["vaos_x"]), len(pav["vaos_y"]),
            pav["area_m2"]),
         "  g = %.2f kN/m2 ; q = %.2f kN/m2 (NBR 6120 Tab.10)"
         % (pav["g_kN_m2"], pav["q_kN_m2"]),
         ""]
    L += ["  FECHAMENTO DE CARGA: %.1f kN nos pilares x %.1f kN esperados "
          "(erro %.3f%%) -> %s"
          % (g["fechamento_carga"]["N_pilares"], g["fechamento_carga"]["esperado"],
             100 * g["fechamento_carga"]["erro_rel"],
             "OK" if g["fechamento_carga"]["OK"] else "NAO FECHA"),
          "  LAJE: h = %.0f cm (declarada %.0f cm) -> %s"
          % (g["laje"]["h_cm"], g["laje_compatibilizada"]["h_declarada_cm"],
             "ATENDE" if g["laje"]["OK"] else "REPROVA"),
          "  VIGAS: %d linhas / %d tramos VERIFICADOS -> %s"
          % (g["vigas"]["n_linhas"], g["vigas"]["n_tramos"],
             "ATENDE" if g["vigas"]["OK"] else "REPROVA"),
          "  PILARES: %d -> %s"
          % (g["pilares"]["n"], "ATENDE" if g["pilares"]["OK"]
             else "REPROVA em " + ", ".join(g["pilares"]["reprovados"]))]
    for motivo in g["vigas"]["reprovadas"]:
        L.append("      [viga] " + motivo)
    if "viga_baldrame" in g:
        bd = g["viga_baldrame"]
        if bd.get("erro"):
            L.append("  VIGA BALDRAME: REPROVA (%s)" % bd["erro"])
        else:
            L.append("  VIGA BALDRAME: %.0f x %.0f cm ; parede %.2f kN/m ; "
                     "fechamento %s -> %s"
                     % (bd["b_cm"], bd["h_cm"], bd["q_parede_kN_m"],
                        "OK" if bd["fechamento_OK"] else "NAO FECHA",
                        "ATENDE" if bd["OK"] else "REPROVA"))
    else:
        L.append("  VIGA BALDRAME: NAO declarada -> o peso da alvenaria do "
                 "terreo NAO entra na fundacao")
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
    if "fundacao" in g:
        fu = g["fundacao"]
        if fu.get("erro"):
            L.append("  FUNDACAO: REPROVA (%s)" % fu["erro"])
        else:
            L.append("  FUNDACAO: %s em %d pilares -> %s"
                     % (fu["tipo"], fu["n_pilares"],
                        "ATENDE" if fu["OK"] else
                        "REPROVA em " + ", ".join(fu["reprovados"])))
    else:
        L.append("  FUNDACAO: NAO dimensionada (sondagem/tensao do solo nao "
                 "declarada)")
    L += ["", "  PILAR MAIS CARREGADO NA FUNDACAO: N = %.1f kN" % r["N_base_max_k"],
          ""]
    L.append("%-8s %-13s %11s %11s %14s"
             % ("PILAR", "POSICAO", "N_pilar(kN)", "N_bald(kN)", "SECAO BASE"))
    L.append("  " + "-" * 62)
    for nome in sorted(r["pilares"]):
        p = r["pilares"][nome]
        base = p["lances"][-1]
        pos = r["descida"]["pilares"][nome]["posicao"]
        L.append("%-8s %-13s %11.1f %11.1f %10.2f x %.2f"
                 % (nome, pos, p["N_base_k"],
                    r["reacoes_baldrame_k"].get(nome, 0.0), base["b"], base["h"]))
    if r.get("planta"):
        L += ["", "  Planta de formas: %s" % r["planta"]]
    L += ["", "  RESULTADO GLOBAL: %s"
          % ("ATENDE" if r["ATENDE"] else "REPROVA -> " + ", ".join(r["reprovados"]))]
    L += ["  [ACAO HORIZONTAL NAO AVALIADA: esta cadeia e' GRAVITACIONAL. Vento,",
          "   desaprumo, gamma_z e ELS de deslocamento lateral nao entram - a",
          "   tipologia cobre ate %d pavimentos e RECUSA mais que isso.]"
          % MAX_PAVIMENTOS,
          "  [A CONFIRMAR: alvenaria ESTRUTURAL nao dimensionada (NBR 16868 ausente",
          "   do acervo); estrutura de telhado em madeira fora do escopo.]"]
    return "\n".join(L)
