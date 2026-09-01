# ============================================================================
# estabilidade_edificio.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Fecha os tres primeiros itens abertos do G3 (REVISAO-G3, secao 10): ate aqui a
# descida de cargas do edificio era GRAVITACIONAL e nada alimentava o gamma_z
# com uma analise de multiplos pavimentos.
#
#   Entra: malha (vaos_x, vaos_y, pe-direito), numero de pavimentos, secoes de
#          pilar e viga, fck, a carga vertical caracteristica de cada pavimento
#          (vinda da descida) e os dados de vento.
#   Calcula: a forca de vento POR PAVIMENTO (NBR 6123), as forcas horizontais
#            ficticias de DESAPRUMO (NBR 6118 11.3.3.4.1), a combinacao a/b/c
#            entre as duas, e o gamma_z (15.5.3) a partir de uma analise de
#            portico plano de 1a ordem com a rigidez reduzida de 15.7.3.
#   NAO dimensiona secao. Devolve esforcos, deslocamentos e a classificacao.
#
# O QUE E' DECLARADO E NAO DERIVADO
# O coeficiente de arrasto Ca da NBR 6123 para edificacao paralelepipedica esta
# na norma APENAS como ABACO (Figuras 4 e 5, confirmado no acervo) - nao existe
# tabela de numeros. Digitalizar curva de imagem foi o que produziu as 6 celulas
# erradas das tabelas de Bares, e e' o mesmo motivo pelo qual o shed multi-vao
# segue bloqueado. Entao Ca e' ENTRADA do projetista, que o le da Figura 4 com
# h/l1 e l1/l2, e a proveniencia fica registrada no resultado.
#
# HIPOTESE DE DISTRIBUICAO (explicita de proposito)
# O vento total de uma direcao e' dividido IGUALMENTE entre os porticos planos
# paralelos aquela direcao. Vale para diafragma rigido e porticos iguais, que e'
# o caso da malha ortogonal regular montada pelo pavimento_tipo. Malha
# irregular ou nucleo rigido exige distribuicao por rigidez - nao e' feito aqui
# e o resultado diz isso.
#
# Referencias conferidas no acervo (NotebookLM), nao de memoria:
#   NBR 6118 11.3.3.4.1, 15.5.1, 15.5.3, 15.7.2, 15.7.3 ; Emenda 1:2026 (a
#   definicao de n passa a ser "numero de pilares que contribuem para o efeito
#   do desaprumo global associados a altura H") ; NBR 6123 4.2.3, 6.3.1, 6.3.6.
# ============================================================================
"""Vento por pavimento, desaprumo e gamma_z do edificio multipavimento."""

from __future__ import annotations

import math

import estabilidade_global_nbr6118 as eg
import fissuracao_nbr6118 as fis
import vento_nbr6123 as vt
from frame2d import Frame2D


THETA_1_MIN = 1.0 / 300.0        # 11.3.3.4.1
THETA_1_MAX = 1.0 / 200.0        # 11.3.3.4.1
# 15.7.3 - rigidez secante aproximada para a analise global de 2a ordem.
# Viga com As' != As (caso geral de viga continua de edificio) -> 0,4.
RIG_PILAR = 0.8
RIG_VIGA = 0.4
MAJORACAO_ECS = 1.10             # 15.5.1: Ecs pode ser majorado em 10 %
GAMMA_F = 1.4                    # ponderacao das acoes no ELU
# ELS - Tabela 13.3, "movimento lateral de edificios": vento na combinacao
# FREQUENTE (psi_1 = 0,30 pela Tabela 11.2), topo <= H/1700 e entre pavimentos
# vizinhos <= Hi/850. A rigidez do ELS NAO e' a de 15.7.3 (que a norma restringe
# a analise de 2a ordem no ELU): 14.6.4.1 manda Ecs com a secao BRUTA.
PSI_1_VENTO = 0.30
LIM_TOPO = 1.0 / 1700.0
LIM_ENTRE_PAVIMENTOS = 1.0 / 850.0
CA_FONTE = ("NBR 6123 Figura 4 (abaco): Ca em funcao de h/l1 e l1/l2 - "
            "lido pelo projetista, nao derivado aqui")


# ---------------------------------------------------------------------------
# desaprumo - NBR 6118 11.3.3.4.1
# ---------------------------------------------------------------------------
def desaprumo(H, n_prumadas, cargas_kN=None, lajes_lisas=False):
    """Imperfeicoes geometricas globais (11.3.3.4.1).

    theta_1 = 1/(100 raiz(H)), limitado a [1/300, 1/200];
    theta_a = theta_1 raiz((1 + 1/n)/2), ou theta_a = theta_1 se lajes lisas.

    Devolve tambem ``theta_a_comparacao``, calculado com o theta_1 BRUTO (sem o
    theta_1min), porque a norma manda comparar com o vento "com desaprumo
    calculado com theta_a, sem a consideracao do theta_1min".

    ``saturou`` diz qual limite mordeu, ou None. Saturar em silencio e' o bug
    que este framework ja encontrou em cinco disciplinas.
    """
    if not (isinstance(H, (int, float)) and H > 0):
        raise ValueError("H (altura total) deve ser numerico > 0")
    if not (isinstance(n_prumadas, int) and n_prumadas > 0):
        raise ValueError("n_prumadas deve ser inteiro > 0")

    bruto = 1.0 / (100.0 * math.sqrt(H))
    saturou = None
    theta_1 = bruto
    if bruto > THETA_1_MAX:
        theta_1, saturou = THETA_1_MAX, "theta_1max"
    elif bruto < THETA_1_MIN:
        theta_1, saturou = THETA_1_MIN, "theta_1min"

    fator = 1.0 if lajes_lisas else math.sqrt((1.0 + 1.0 / n_prumadas) / 2.0)
    theta_a = theta_1 * fator
    theta_a_comparacao = bruto * fator

    forcas = [theta_a * float(P) for P in (cargas_kN or [])]
    return {"theta_1": theta_1, "theta_1_bruto": bruto, "theta_a": theta_a,
            "theta_a_comparacao": theta_a_comparacao, "saturou": saturou,
            "lajes_lisas": bool(lajes_lisas), "n_prumadas": n_prumadas,
            "H_m": float(H), "forcas_kN": forcas}


# ---------------------------------------------------------------------------
# vento por pavimento - NBR 6123
# ---------------------------------------------------------------------------
def _cotas_e_areas(n_pav, pe_direito, l1):
    """Cota de cada pavimento e a sua area frontal tributaria.

    A faixa tributaria do pavimento i vai de z_i - pe/2 a z_i + pe/2, exceto o
    ultimo, que termina no topo. A meia-altura inferior (0 a pe/2) desce direto
    para a fundacao e NAO e' atribuida a nenhum pavimento.
    """
    itens = []
    for i in range(1, n_pav + 1):
        z = i * pe_direito
        h_trib = pe_direito if i < n_pav else pe_direito / 2.0
        itens.append({"pavimento": i, "z_m": z, "h_trib_m": h_trib,
                      "Ae_m2": l1 * h_trib})
    return itens


def vento_por_pavimento(spec, direcao="x"):
    """Forca de arrasto de cada pavimento (NBR 6123 4.2.3: Fa = Ca q Ae).

    ``direcao`` e' a direcao de SOPRO do vento. l1 (largura frontal) e' a
    dimensao perpendicular a ela.
    """
    if direcao not in ("x", "y"):
        raise ValueError("direcao deve ser 'x' ou 'y'")
    geo = spec["geometria"]
    vento = spec.get("vento") or {}
    ca_decl = vento.get("ca")
    if not isinstance(ca_decl, dict) or direcao not in ca_decl:
        raise ValueError(
            "vento.ca['%s'] nao foi declarado. %s" % (direcao, CA_FONTE))
    ca = ca_decl[direcao]
    if not (isinstance(ca, (int, float)) and not isinstance(ca, bool) and ca > 0):
        raise ValueError("vento.ca['%s'] deve ser numerico > 0" % direcao)

    # l1 = perpendicular ao vento ; l2 = na direcao do vento (NBR 6123 2.2)
    l1 = float(sum(geo["vaos_y"] if direcao == "x" else geo["vaos_x"]))
    l2 = float(sum(geo["vaos_x"] if direcao == "x" else geo["vaos_y"]))
    n_pav = int(spec["n_pavimentos"])
    pe = float(geo["pe_direito"])
    H = n_pav * pe

    v0 = vento["v0"]
    cat, classe = vento["cat"], vento["classe"]
    s1, s3 = vento.get("s1", 1.0), vento.get("s3", 1.0)

    pavimentos = []
    for item in _cotas_e_areas(n_pav, pe, l1):
        _, _, _, s2 = vt.s2_factor(cat, classe, item["z_m"])
        vk = v0 * s1 * s2 * s3
        q = 0.613 * vk ** 2 / 1000.0          # kN/m2
        fa = ca * q * item["Ae_m2"]
        pavimentos.append({**item, "s2": s2, "vk_m_s": vk, "q_kN_m2": q,
                           "Fa_kN": fa})

    m_base = sum(p["Fa_kN"] * p["z_m"] for p in pavimentos)
    return {"direcao": direcao, "l1_m": l1, "l2_m": l2, "h_l1": H / l1,
            "l1_l2": l1 / l2, "H_m": H, "ca": ca,
            "ca_proveniencia": "declarado", "ca_fonte": CA_FONTE,
            "pavimentos": pavimentos,
            "F_total_kN": sum(p["Fa_kN"] for p in pavimentos),
            "M_base_kNm": m_base}


# ---------------------------------------------------------------------------
# combinacao vento x desaprumo - 11.3.3.4.1 alineas a) b) c)
# ---------------------------------------------------------------------------
def combina_vento_desaprumo(M_vento, M_desaprumo):
    """Regra dos 30 % comparada pelos momentos totais na base.

    a) 30 % do vento MAIOR que o desaprumo -> so vento;
    b) vento INFERIOR a 30 % do desaprumo  -> so desaprumo, com theta_1min;
    c) demais casos -> combina, sem theta_1min.
    """
    mv, md = float(M_vento), float(M_desaprumo)
    if mv < 0 or md < 0:
        raise ValueError("momentos de comparacao devem ser >= 0")
    if 0.30 * mv > md:
        return {"caso": "a", "usar": "vento", "M_kNm": mv,
                "aplica_theta_1min": False,
                "motivo": "30 %% do vento (%.1f) > desaprumo (%.1f): "
                          "so vento (11.3.3.4.1-a)" % (0.30 * mv, md)}
    if mv < 0.30 * md:
        return {"caso": "b", "usar": "desaprumo", "M_kNm": md,
                "aplica_theta_1min": True,
                "motivo": "vento (%.1f) < 30 %% do desaprumo (%.1f): so "
                          "desaprumo com theta_1min (11.3.3.4.1-b)"
                          % (mv, 0.30 * md)}
    return {"caso": "c", "usar": "combinado", "M_kNm": mv + md,
            "aplica_theta_1min": False,
            "motivo": "caso intermediario: combina vento + desaprumo sem "
                      "theta_1min (11.3.3.4.1-c)"}


# ---------------------------------------------------------------------------
# gamma_z - 15.5.3 / 15.7.2 / 15.7.3
# ---------------------------------------------------------------------------
def classifica_gamma_z(gz):
    """Classifica o gamma_z e devolve o majorador de 15.7.2.

    gamma_z <= 1,1 -> nos fixos, 2a ordem global dispensavel;
    1,1 < gamma_z <= 1,3 -> nos moveis, majorar horizontais por 0,95 gamma_z;
    gamma_z > 1,3 -> o processo simplificado NAO vale. REPROVA - nao existe
    majorador que salve, e devolver OK aqui seria saturar em silencio.
    """
    majorador, motivo = eg.majoracao_horizontal(gz)
    return {"gamma_z": gz, "nos": "fixos" if gz <= 1.1 else "moveis",
            "majorador": majorador, "motivo": motivo,
            "OK": majorador is not None}


def _portico_plano(vaos, n_pav, pe, secoes, Ec, rig_pilar=RIG_PILAR,
                   rig_viga=RIG_VIGA, pilar_axial_rigido=False):
    """Monta o portico plano de um alinhamento.

    A reducao de rigidez entra na INERCIA (I = coef * Ic) e nao no modulo, para
    nao reduzir junto a rigidez AXIAL dos pilares, que a norma nao manda
    reduzir. Com ``rig_pilar = rig_viga = 1,0`` sai a secao bruta do ELS.

    ``pilar_axial_rigido`` suprime o encurtamento axial dos pilares (area
    inflada). E' a Nota f da Tabela 13.3: no deslocamento lateral entre
    pavimentos "nao podem ser incluidos os deslocamentos devidos a deformacoes
    axiais nos pilares".
    """
    fr = Frame2D()
    n_col = len(vaos) + 1
    xs = [0.0]
    for v in vaos:
        xs.append(xs[-1] + v)

    # nos: nivel 0 (base) ate n_pav
    def no(nivel, col):
        return nivel * n_col + col

    for nivel in range(n_pav + 1):
        for x in xs:
            fr.add_node(x, nivel * pe)

    pil, vig = secoes["pilar"], secoes["viga"]
    I_pil = rig_pilar * eg.inercia_retangular(pil["b"], pil["h"])
    A_pil = pil["b"] * pil["h"] * (1e6 if pilar_axial_rigido else 1.0)
    I_vig = rig_viga * eg.inercia_retangular(vig["b"], vig["h"])
    A_vig = vig["b"] * vig["h"]

    for nivel in range(n_pav):                       # pilares
        for col in range(n_col):
            fr.add_element(no(nivel, col), no(nivel + 1, col), Ec, A_pil, I_pil)
    for nivel in range(1, n_pav + 1):                # vigas
        for col in range(n_col - 1):
            fr.add_element(no(nivel, col), no(nivel, col + 1), Ec, A_vig, I_vig)
    for col in range(n_col):                         # engaste na fundacao
        fr.add_support(no(0, col), u=True, v=True, rot=True)
    return fr, no, n_col


def _portico_plano_heterogeneo(vaos, n_pav, pe, secoes_pilares, secao_viga, Ec,
                               rig_pilar=1.0, rig_viga=1.0,
                               pilar_axial_rigido=False):
    """Portico plano com secao DIFERENCIADA por prumada (G17).

    ``secoes_pilares``: lista de {b,h} com tamanho n_col = len(vaos)+1, na ordem
    das colunas da esquerda para a direita. Cada pilar tem sua inercia/area
    propria, ao contrario de ``_portico_plano`` que usa uma secao unica (a menor
    do lance da base).

    Por que heterogeneo? O _portico_plano uniforme usa a MENOR secao do lance
    da base: conservador para gamma_z (menor rigidez -> maior deslocamento) mas
    NAO conservador para esforcos – um pilar interno robusto atrai mais momento
    que um canto esbelto e fica subestimado por um modelo uniforme. Para M_base
    por pilar a prumada individual importa.

    ``rig_pilar=rig_viga=1.0`` com ``Ec=Ecs`` (14.6.4.1, secao bruta) e' a rigidez
    do ELS/fundacao, DISTINTA da rigidez 15.7.3 (0,8/0,4 com 1,10*Ecs) usada para
    gamma_z no ELU. Reusar o mesmo modelo repetiria o erro que o G11 pegou
    (reusar rigidez de ELU no ELS dobrando deslocamento). G17 documenta a
    separacao.
    """
    fr = Frame2D()
    n_col = len(vaos) + 1
    if len(secoes_pilares) != n_col:
        raise ValueError("secoes_pilares deve ter n_col = len(vaos)+1 elementos")
    xs = [0.0]
    for v in vaos:
        xs.append(xs[-1] + v)

    def no(nivel, col):
        return nivel * n_col + col

    for nivel in range(n_pav + 1):
        for x in xs:
            fr.add_node(x, nivel * pe)

    # vigas: uniformes
    I_vig = rig_viga * eg.inercia_retangular(secao_viga["b"], secao_viga["h"])
    A_vig = secao_viga["b"] * secao_viga["h"]

    # pilares: um por coluna, com inercia propria
    for nivel in range(n_pav):
        for col in range(n_col):
            pil = secoes_pilares[col]
            I_pil = rig_pilar * eg.inercia_retangular(pil["b"], pil["h"])
            A_pil = pil["b"] * pil["h"] * (1e6 if pilar_axial_rigido else 1.0)
            fr.add_element(no(nivel, col), no(nivel + 1, col), Ec, A_pil, I_pil)
    for nivel in range(1, n_pav + 1):
        for col in range(n_col - 1):
            fr.add_element(no(nivel, col), no(nivel, col + 1), Ec, A_vig, I_vig)
    for col in range(n_col):
        fr.add_support(no(0, col), u=True, v=True, rot=True)
    return fr, no, n_col


def gamma_z_direcao(spec, direcao, forcas_horizontais_kN, cargas_verticais_kN):
    """gamma_z de uma direcao a partir de uma analise de portico de 1a ordem.

    ``forcas_horizontais_kN`` e ``cargas_verticais_kN`` sao os valores
    CARACTERISTICOS por pavimento, do 1o ao ultimo; a ponderacao de calculo e'
    aplicada aqui.
    """
    geo = spec["geometria"]
    # o vento em x e' resistido pelos porticos alinhados em x
    vaos = geo["vaos_x"] if direcao == "x" else geo["vaos_y"]
    n_porticos = len(geo["vaos_y"] if direcao == "x" else geo["vaos_x"]) + 1
    n_pav = int(spec["n_pavimentos"])
    pe = float(geo["pe_direito"])
    Ecs = fis.modulo_secante(spec["materiais"]["fck"])
    Ec = MAJORACAO_ECS * Ecs

    fr, no, n_col = _portico_plano(vaos, n_pav, pe, spec["secoes"], Ec)

    # Carrega o portico com a parcela de calculo que lhe cabe.
    for nivel in range(1, n_pav + 1):
        h_d = GAMMA_F * forcas_horizontais_kN[nivel - 1] / n_porticos
        p_d = GAMMA_F * cargas_verticais_kN[nivel - 1] / n_porticos
        fr.add_nodal_load(no(nivel, 0), Fx=h_d)          # forca no plano do piso
        for col in range(n_col):                          # peso distribuido nos pilares
            fr.add_nodal_load(no(nivel, col), Fy=-p_d / n_col)

    d, _ = fr.solve()

    # M1,tot,d = soma dos momentos das horizontais de calculo na base
    m1 = sum(GAMMA_F * forcas_horizontais_kN[i - 1] / n_porticos * (i * pe)
             for i in range(1, n_pav + 1))
    # dM,tot,d = soma (verticais de calculo x deslocamento horizontal do ponto)
    dm = 0.0
    deslocamentos = []
    for nivel in range(1, n_pav + 1):
        u = sum(d[3 * no(nivel, col)] for col in range(n_col)) / n_col
        deslocamentos.append(u)
        dm += GAMMA_F * cargas_verticais_kN[nivel - 1] / n_porticos * u

    if m1 <= 0:
        raise ValueError("M1,tot,d nulo: sem acao horizontal para avaliar gamma_z")
    if dm >= m1:
        raise ValueError("dM,tot,d >= M1,tot,d: estrutura instavel, gamma_z "
                         "nao definido (15.5.3)")
    gz = eg.gamma_z(dm, m1)
    return {"gamma_z": gz, "dM_tot_d_kNm": dm, "M1_tot_d_kNm": m1,
            "deslocamento_topo_m": deslocamentos[-1],
            "deslocamentos_m": deslocamentos, "n_porticos": n_porticos,
            "Ecs_kN_m2": Ecs, "Ec_kN_m2": Ec,
            "rigidez": {"pilar": RIG_PILAR, "viga": RIG_VIGA,
                        "majoracao_Ecs": MAJORACAO_ECS},
            **classifica_gamma_z(gz)}


# ---------------------------------------------------------------------------
# ELS - deslocamento lateral (13.3, Tabela 13.3)
# ---------------------------------------------------------------------------
def deslocamento_els(spec, direcao, forcas_vento_kN):
    """Movimento lateral do edificio na combinacao FREQUENTE de servico.

    Rigidez do ELS: Ecs com a secao BRUTA (14.6.4.1), sem as reducoes de
    15.7.3, que a norma restringe a analise de 2a ordem no ELU e que aqui
    dobrariam o deslocamento sem amparo.

    So o vento entra: a Tabela 13.3 limita o movimento lateral "provocado pela
    acao do vento", e a Nota f manda excluir as deformacoes axiais dos pilares,
    o que aqui e' feito tornando os pilares axialmente rigidos.
    """
    geo = spec["geometria"]
    vaos = geo["vaos_x"] if direcao == "x" else geo["vaos_y"]
    n_porticos = len(geo["vaos_y"] if direcao == "x" else geo["vaos_x"]) + 1
    n_pav = int(spec["n_pavimentos"])
    pe = float(geo["pe_direito"])
    Ecs = fis.modulo_secante(spec["materiais"]["fck"])

    fr, no, n_col = _portico_plano(vaos, n_pav, pe, spec["secoes"], Ecs,
                                   rig_pilar=1.0, rig_viga=1.0,
                                   pilar_axial_rigido=True)
    for nivel in range(1, n_pav + 1):
        h = PSI_1_VENTO * forcas_vento_kN[nivel - 1] / n_porticos
        fr.add_nodal_load(no(nivel, 0), Fx=h)
    d, _ = fr.solve()

    u = [sum(d[3 * no(nivel, col)] for col in range(n_col)) / n_col
         for nivel in range(1, n_pav + 1)]
    H = n_pav * pe
    u_topo = u[-1]
    lim_topo = LIM_TOPO * H
    entre = [u[0]] + [u[i] - u[i - 1] for i in range(1, n_pav)]
    lim_entre = LIM_ENTRE_PAVIMENTOS * pe
    pior = max(entre)
    return {"psi_1": PSI_1_VENTO, "Ecs_kN_m2": Ecs, "secao": "bruta",
            "u_topo_m": u_topo, "limite_topo_m": lim_topo,
            "topo_OK": u_topo <= lim_topo,
            "H_sobre_u": (H / u_topo) if u_topo > 0 else float("inf"),
            "drift_entre_pavimentos_m": entre,
            "pior_drift_m": pior, "limite_entre_m": lim_entre,
            "entre_OK": pior <= lim_entre,
            "Hi_sobre_drift": (pe / pior) if pior > 0 else float("inf"),
            "OK": u_topo <= lim_topo and pior <= lim_entre,
            "referencia": "NBR 6118 Tabela 13.3 (H/1700 e Hi/850), combinacao "
                          "frequente psi_1 = 0,30; rigidez de 14.6.4.1"}


# ---------------------------------------------------------------------------
# gate consolidado
# ---------------------------------------------------------------------------
def verifica(spec):
    """Vento + desaprumo + gamma_z nas duas direcoes. Devolve o gate."""
    geo = spec["geometria"]
    n_pav = int(spec["n_pavimentos"])
    pe = float(geo["pe_direito"])
    H = n_pav * pe
    cargas = list(spec["cargas_verticais_kN"])
    if len(cargas) != n_pav:
        raise ValueError("cargas_verticais_kN deve ter um valor por pavimento")
    if not all(isinstance(c, (int, float)) and c > 0 for c in cargas):
        raise ValueError("toda carga vertical de pavimento deve ser > 0")

    por_direcao = {}
    for direcao in ("x", "y"):
        vento = vento_por_pavimento(spec, direcao)
        # n = pilares que contribuem para o desaprumo global (Emenda 1:2026)
        n_prumadas = (len(geo["vaos_x"]) + 1) * (len(geo["vaos_y"]) + 1)
        desap = desaprumo(H, n_prumadas, cargas,
                          lajes_lisas=bool(spec.get("lajes_lisas")))
        m_desap = sum(f * ((i + 1) * pe) for i, f in enumerate(desap["forcas_kN"]))
        # a comparacao usa theta_a SEM theta_1min (11.3.3.4.1)
        razao = desap["theta_a_comparacao"] / desap["theta_a"]
        combinacao = combina_vento_desaprumo(vento["M_base_kNm"], m_desap * razao)

        if combinacao["usar"] == "vento":
            horizontais = [p["Fa_kN"] for p in vento["pavimentos"]]
        elif combinacao["usar"] == "desaprumo":
            horizontais = list(desap["forcas_kN"])
        else:
            horizontais = [p["Fa_kN"] + f for p, f
                           in zip(vento["pavimentos"], desap["forcas_kN"])]

        gz = gamma_z_direcao(spec, direcao, horizontais, cargas)
        els = deslocamento_els(spec, direcao,
                               [p["Fa_kN"] for p in vento["pavimentos"]])
        gz["aplicavel"] = n_pav >= 4
        gz["motivo_aplicabilidade"] = (
            "" if n_pav >= 4 else
            "15.5.3: gamma_z e' valido para no minimo quatro andares; com "
            "%d pavimentos usar o parametro alpha de 15.5.2" % n_pav)
        por_direcao[direcao] = {
            "vento": vento, "desaprumo": desap, "combinacao": combinacao,
            "forcas_horizontais_kN": horizontais, "gamma_z": gz["gamma_z"],
            "detalhe_gamma_z": gz, "els": els,
            "OK": (gz["OK"] and els["OK"]) if n_pav >= 4 else None}

    critica = max(por_direcao, key=lambda k: por_direcao[k]["gamma_z"])
    detalhe = por_direcao[critica]["detalhe_gamma_z"]
    aplicavel = n_pav >= 4
    return {"direcoes": ["x", "y"], "por_direcao": por_direcao,
            "direcao_critica": critica,
            "gamma_z": {"gamma_z": detalhe["gamma_z"],
                        "dM_tot_d_kNm": detalhe["dM_tot_d_kNm"],
                        "M1_tot_d_kNm": detalhe["M1_tot_d_kNm"],
                        "deslocamento_topo_m": detalhe["deslocamento_topo_m"],
                        "rigidez": detalhe["rigidez"],
                        "nos": detalhe["nos"], "majorador": detalhe["majorador"],
                        "aplicavel": aplicavel,
                        "motivo": detalhe["motivo"] if aplicavel else
                        ("15.5.3: gamma_z e' valido para no minimo quatro "
                         "andares; com %d pavimentos usar o parametro alpha "
                         "de 15.5.2" % n_pav)},
            "els": por_direcao[critica]["els"],
            "els_OK": all(por_direcao[d]["els"]["OK"] for d in ("x", "y")),
            "H_m": H, "n_pavimentos": n_pav,
            "OK": (bool(detalhe["OK"]) and
                   all(por_direcao[d]["els"]["OK"] for d in ("x", "y")))
                  if aplicavel else None}


# ---------------------------------------------------------------------------
# G17 - momento na base por prumada (extrai M_base por pilar das duas direcoes)
# ---------------------------------------------------------------------------
def _momentos_linha(vaos, n_pav, pe, secoes_pilares_linha, secao_viga, Ecs,
                    cargas_verticais_kN, forcas_horizontais_kN, n_porticos):
    """Resolve UM alinhamento (uma linha de portico) e extrai M/V na base.

    Usa secao BRUTA (Ecs, rig=1,0) por prumada – distinta da rigidez reduzida
    15.7.3 usada para gamma_z. Heterogeneo: cada coluna tem sua secao real.
    Devolve lista de {M_kNm, V_kN} por coluna (ordem esquerda->direita), em
    valores CARACTERISTICOS (sem gamma_f).
    """
    fr, no, n_col = _portico_plano_heterogeneo(
        vaos, n_pav, pe, secoes_pilares_linha, secao_viga, Ecs,
        rig_pilar=1.0, rig_viga=1.0)
    # cargas caracteristicas por portico
    for nivel in range(1, n_pav + 1):
        h_k = forcas_horizontais_kN[nivel - 1] / n_porticos
        p_k = cargas_verticais_kN[nivel - 1] / n_porticos
        fr.add_nodal_load(no(nivel, 0), Fx=h_k)
        for col in range(n_col):
            fr.add_nodal_load(no(nivel, col), Fy=-p_k / n_col)
    _, mf = fr.solve()
    out = []
    for col in range(n_col):
        idx = col  # pilar da base, nivel 0
        f = mf[idx]
        # f = [N_i, V_i, M_i, N_j, V_j, M_j] local – M_i e' o momento na base
        # (sinal depende da convencao do elemento; para dimensionamento o modulo
        # governa a excentricidade e = |M|/N)
        out.append({"M_kNm": float(f[2]), "M_abs_kNm": abs(float(f[2])),
                    "V_kN": float(f[1]), "V_abs_kN": abs(float(f[1])),
                    "N_kN": float(f[0])})
    return out


def momentos_base_por_pilar(spec, pilares, estabilidade=None):
    """M_base caracteristico por pilar nas duas direcoes (G17).

    Extrai o momento fletor na base de CADA prumada a partir do mesmo modelo
    de portico plano que alimenta gamma_z, mas com duas correcoes que o G17
    exige:

    * SECAO POR PRUMADA (heterogeneo): o modelo de gamma_z usa a MENOR secao
      do lance da base para TODOS os pilares (conservador para deslocamento).
      Para esforcos isso subestima o pilar central robusto em ~2x e superestima
      o canto esbelto (ver comparativo G17). Aqui cada linha monta com as secoes
      REAIS daquela prumada.

    * RIGIDEZ BRUTA (Ecs, 1,0) em vez de 0,8/0,4 com 1,10*Ecs (15.7.3): 15.7.3 e'
      exclusiva da analise global de 2a ordem no ELU; 14.6.4.1 manda Ecs com secao
      bruta no ELS. Reusar a rigidez de ELU para extrair momento caracteristico
      repete o erro que o G11 pegou (deslocamento ELS dobrado). A escolha fica
      documentada no retorno (``rigidez_momento``).

    ``spec``: {geometria{vaos_x,vaos_y,pe_direito}, n_pavimentos, materiais{fck},
              secoes{viga{b,h}}, cargas_verticais_kN, vento, lajes_lisas?}
              – as secoes de pilar individuais vêm de ``pilares``, nao de spec.
    ``pilares``: lista de {nome, i, j, secao(b,h)} – ``secao`` e' a do lance da
                BASE (que define o balanco da sapata). i=indice em vaos_x (0..nx),
                j=indice em vaos_y (0..ny).
    ``estabilidade``: (opc) retorno de ``verifica(spec)`` – reusado para nao
                      recalcular vento/desaprumo; se None, recalcula internamente.

    Retorna {nome: {Mx_kNm, Mx_abs_kNm, My_kNm, My_abs_kNm, Vx_kN, Vy_kN,
                     posicao, i, j}, ...}  com ``_proveniencia`` e ``_rigidez``.
    """
    geo = spec["geometria"]
    n_pav = int(spec["n_pavimentos"])
    pe = float(geo["pe_direito"])
    fck = spec["materiais"]["fck"]
    Ecs = fis.modulo_secante(fck)
    cargas = list(spec["cargas_verticais_kN"])
    if len(cargas) != n_pav:
        raise ValueError("cargas_verticais_kN deve ter um valor por pavimento")
    # indexa pilares por coordenada (i,j)
    por_coord = {(p["i"], p["j"]): p for p in pilares}
    # horizontais por direcao (reusa estabilidade quando possivel)
    horizontais = {}
    if estabilidade is not None:
        for d in ("x", "y"):
            blk = (estabilidade.get("por_direcao") or {}).get(d)
            if blk is not None and "forcas_horizontais_kN" in blk:
                horizontais[d] = list(blk["forcas_horizontais_kN"])
    if "x" not in horizontais or "y" not in horizontais:
        # recalcula vento+desaprumo+combinacao (mesma regra de verifica)
        H = n_pav * pe
        n_prumadas = (len(geo["vaos_x"]) + 1) * (len(geo["vaos_y"]) + 1)
        for direcao in ("x", "y"):
            if direcao in horizontais:
                continue
            vento = vento_por_pavimento(spec, direcao)
            desap = desaprumo(H, n_prumadas, cargas,
                              lajes_lisas=bool(spec.get("lajes_lisas")))
            m_desap = sum(f * ((idx + 1) * pe) for idx, f in enumerate(desap["forcas_kN"]))
            razao = desap["theta_a_comparacao"] / desap["theta_a"]
            comb = combina_vento_desaprumo(vento["M_base_kNm"], m_desap * razao)
            if comb["usar"] == "vento":
                horizontais[direcao] = [p["Fa_kN"] for p in vento["pavimentos"]]
            elif comb["usar"] == "desaprumo":
                horizontais[direcao] = list(desap["forcas_kN"])
            else:
                horizontais[direcao] = [p["Fa_kN"] + f for p, f
                                        in zip(vento["pavimentos"], desap["forcas_kN"])]
    # secao da viga (uniforme no predio)
    sec_viga = spec["secoes"]["viga"] if "secoes" in spec and "viga" in spec["secoes"] else {"b": 0.20, "h": 0.50}
    # prepara saida zerada
    resultado = {}
    for p in pilares:
        resultado[p["nome"]] = {"nome": p["nome"], "i": p["i"], "j": p["j"],
                                "posicao": p.get("posicao"),
                                "Mx_kNm": 0.0, "Mx_abs_kNm": 0.0,
                                "My_kNm": 0.0, "My_abs_kNm": 0.0,
                                "Vx_kN": 0.0, "Vy_kN": 0.0,
                                "secao": p.get("secao")}

    # --- direcao X: porticos paralelos a X, varrem j (linhas em Y) -----------
    vaos_x = list(geo["vaos_x"])
    n_porticos_x = len(geo["vaos_y"]) + 1
    for j in range(n_porticos_x):
        # secoes desta linha j, ordenadas por i
        linha_secoes = []
        linha_nomes = []
        for i in range(len(vaos_x) + 1):
            chave = (i, j)
            pil = por_coord.get(chave)
            if pil is None:
                raise ValueError("pilar (%d,%d) nao encontrado para direcao x linha %d" % (i, j, j))
            sec = pil.get("secao")
            if sec is None:
                # fallback: usa a primeira secao de pilares se nao houver
                raise ValueError("pilar %s sem secao" % pil["nome"])
            # secao vem como (b,h) tupla ou dict
            if isinstance(sec, (list, tuple)) and len(sec) == 2:
                b, h = float(sec[0]), float(sec[1])
            elif isinstance(sec, dict) and "b" in sec and "h" in sec:
                b, h = float(sec["b"]), float(sec["h"])
            else:
                raise ValueError("secao do pilar %s invalida: %r" % (pil["nome"], sec))
            linha_secoes.append({"b": b, "h": h})
            linha_nomes.append(pil["nome"])
        momentos_linha = _momentos_linha(
            vaos_x, n_pav, pe, linha_secoes, sec_viga, Ecs,
            cargas, horizontais["x"], n_porticos_x)
        for nome, vals in zip(linha_nomes, momentos_linha):
            resultado[nome]["Mx_kNm"] = round(vals["M_kNm"], 3)
            resultado[nome]["Mx_abs_kNm"] = round(vals["M_abs_kNm"], 3)
            resultado[nome]["Vx_kN"] = round(vals["V_kN"], 3)
            resultado[nome]["Vx_abs_kN"] = round(vals["V_abs_kN"], 3)

    # --- direcao Y: porticos paralelos a Y, varrem i (linhas em X) -----------
    vaos_y = list(geo["vaos_y"])
    n_porticos_y = len(geo["vaos_x"]) + 1
    for i in range(n_porticos_y):
        linha_secoes = []
        linha_nomes = []
        for j in range(len(vaos_y) + 1):
            chave = (i, j)
            pil = por_coord.get(chave)
            if pil is None:
                raise ValueError("pilar (%d,%d) nao encontrado para direcao y linha %d" % (i, j, i))
            sec = pil.get("secao")
            if isinstance(sec, (list, tuple)) and len(sec) == 2:
                b, h = float(sec[0]), float(sec[1])
            elif isinstance(sec, dict) and "b" in sec and "h" in sec:
                b, h = float(sec["b"]), float(sec["h"])
            else:
                raise ValueError("secao do pilar %s invalida: %r" % (pil["nome"], sec))
            linha_secoes.append({"b": b, "h": h})
            linha_nomes.append(pil["nome"])
        momentos_linha = _momentos_linha(
            vaos_y, n_pav, pe, linha_secoes, sec_viga, Ecs,
            cargas, horizontais["y"], n_porticos_y)
        for nome, vals in zip(linha_nomes, momentos_linha):
            resultado[nome]["My_kNm"] = round(vals["M_kNm"], 3)
            resultado[nome]["My_abs_kNm"] = round(vals["M_abs_kNm"], 3)
            resultado[nome]["Vy_kN"] = round(vals["V_kN"], 3)
            resultado[nome]["Vy_abs_kN"] = round(vals["V_abs_kN"], 3)

    # anexa metadados
    for nome in resultado:
        resultado[nome]["M_resultante_kNm"] = round(
            math.hypot(resultado[nome]["Mx_abs_kNm"], resultado[nome]["My_abs_kNm"]), 3)
    resultado["_proveniencia"] = (
        "M_base por prumada extraido do portico plano heterogeneo (secao real por "
        "pilar), rigidez BRUTA Ecs (14.6.4.1), CARGAS caracteristicas (sem gamma_f) "
        "divididas igualmente entre porticos paralelos (hipotese diafragma rigido)")
    resultado["_rigidez_momento"] = {"Ecs_kN_m2": Ecs, "rig_pilar": 1.0,
                                     "rig_viga": 1.0, "secao": "bruta",
                                     "heterogeneo": True,
                                     "nota": "distinta da rigidez 15.7.3 (0,8/0,4 com 1,10*Ecs) usada para gamma_z"}
    resultado["_horizontais_kN"] = {d: list(horizontais[d]) for d in ("x", "y")}
    return resultado


def relatorio_pt(r):
    """Quadro-resumo da estabilidade horizontal do edificio."""
    L = ["ESTABILIDADE HORIZONTAL DO EDIFICIO (NBR 6118 11.3.3.4.1 / 15.5.3)",
         "  H = %.2f m em %d pavimentos" % (r["H_m"], r["n_pavimentos"])]
    for d in r["direcoes"]:
        bloco = r["por_direcao"][d]
        des = bloco["desaprumo"]
        L.append("  direcao %s: vento F = %.1f kN ; desaprumo theta_a = 1/%.0f%s"
                 % (d, bloco["vento"]["F_total_kN"], 1.0 / des["theta_a"],
                    "" if not des["saturou"] else " (saturou em %s)" % des["saturou"]))
        L.append("    %s" % bloco["combinacao"]["motivo"])
        L.append("    gamma_z = %.3f -> nos %s"
                 % (bloco["gamma_z"], bloco["detalhe_gamma_z"]["nos"]))
        els = bloco["els"]
        L.append("    ELS topo H/%.0f (limite H/1700) %s ; entre pav. Hi/%.0f "
                 "(limite Hi/850) %s"
                 % (els["H_sobre_u"], "OK" if els["topo_OK"] else "NAO ATENDE",
                    els["Hi_sobre_drift"],
                    "OK" if els["entre_OK"] else "NAO ATENDE"))
    L.append("  direcao critica: %s ; %s" % (r["direcao_critica"],
                                             r["gamma_z"]["motivo"]))
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))
