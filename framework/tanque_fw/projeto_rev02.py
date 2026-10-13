# ============================================================================
# projeto_rev02.py - TANQUE-BASE INTEGRAL: PROJETO DA REV.02
#
# Fecha o que a REV.01 deixou "pendente calculo". A concepcao segue o produto
# de serie equivalente (tanque de dejetos Containex 20', descricao tecnica de
# 22.02.2024): gaiola de tubos com longarinas embaixo e em cima, 6 pontos de
# apoio (4 cantos + 2 no meio dos lados longos), tanque de chapa dentro da
# gaiola, transporte so' vazio.
#
# Tudo e' parametrico em SPEC_REV02: mudar uma dimensao refaz as contas.
#
# O QUE E' NORMA E O QUE E' ADOTADO
#  - resistencias e coeficientes: NBR 8800:2024, NBR 8261:2019, ASTM A36,
#    ISO 668/1496-1 (lidos no MCP_Fontes ou ja' conferidos no motor do galpao);
#  - valores ADOTADOS (pressao de projeto, sobre-espessura de corrosao, carga
#    por canto, fator dinamico de icamento, perdas no respiro) estao em
#    spec["adotado"] e saem listados na memoria como premissa a confirmar.
# ============================================================================
"""Dimensionamento do tanque-base integral (REV.02)."""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "galpao_fw"))
from check_nbr8800 import GA1, chi_compressao  # noqa: E402  NBR 8800 5.3.3
from ligacoes import GW2                        # noqa: E402  NBR 8800:2024 Tabela 9, nota i
from solda_perfil_chapa import perna_minima     # noqa: E402  NBR 8800:2024 Tabela 11

import tanque_base as TB                        # noqa: E402

E_ACO = 200000.0      # MPa - NBR 8800:2024, 4.6.2.9
G = 9.80665           # m/s2
FY_A36 = 250.0        # MPa - ASTM A36/A36M-19, Tabela 2
FW_E70 = 485.0        # MPa - metal de solda E70 (valor ja' usado em ligacoes.py)
# NBR 8800 (combinacoes normais), como no portico do galpao: peso proprio de
# estrutura metalica 1,25; acao variavel 1,50. O liquido entra como VARIAVEL.
# 1,25 conferido na NBR 8681:2025, Tabela 1 (peso proprio de estruturas de aco).
GAMA_G, GAMA_Q = 1.25, 1.50
GAMA_VENTO = 1.40
# NBR 8800:2024, Tabela B.1 (B.3.4): vigas de piso
FLECHA_LIMITE_BARRA = 350.0
# NBR 9050:2020, 6.8.2: degraus
ESPELHO_MIN, ESPELHO_MAX, PISO_MIN, PISO_MAX = 160.0, 180.0, 280.0, 320.0
# ISO 668:2020/Amd.1:2022, Tabela 2 - massa bruta maxima do conteiner 1CC
R_ISO_1CC = 36000.0   # kg
# ISO 668:2020, Tabela A.1 - distancia entre centros dos cantos, 1CC
S_CANTOS, P_CANTOS = 5853.0, 2259.0  # mm
# ISO 668:2020, secao 4 - altura do conteiner 1CC
H_CONTEINER_1CC = 2591.0  # mm
# NBR 6123:2023, Tabela 3 - fator S2 para z <= 5 m, por categoria e classe
# (lido no MCP_Fontes em 2026-10-13; confere com bm.Fr.(z/10)^p das Tabelas 1 e 2)
S2_ATE_5M = {"I": {"A": 1.06, "B": 1.04, "C": 1.01}, "II": {"A": 0.94, "B": 0.92, "C": 0.89},
             "III": {"A": 0.88, "B": 0.86, "C": 0.82}, "IV": {"A": 0.79, "B": 0.76, "C": 0.73},
             "V": {"A": 0.74, "B": 0.72, "C": 0.67}}
# NBR 6122:2022, 7.7.1 - sapata isolada ou bloco: nenhuma dimensao em planta abaixo de 60 cm
LADO_MIN_SAPATA = 600.0  # mm

SPEC_REV02 = {
    "documento": "PRU-CT-SAN-RES-001/2026 REV.02",
    "skid": {"comp": 6058.0, "larg": 2438.0, "alt": 690.0},
    "tubo_quadro": {"h": 150.0, "b": 100.0, "t": 6.35},     # longarinas, testeiras e montantes
    # travessa inferior em pe' (100 mm): deitada, a flecha com o tanque cheio passava de vao/220
    "tubo_travessa_inf": {"h": 100.0, "b": 50.0, "t": 4.75},
    "tubo_travessa_sup": {"h": 50.0, "b": 100.0, "t": 4.75},  # deitada: 50 mm de altura
    "grau_tubo": "B",                                       # NBR 8261
    "passo_travessa_max": 500.0,
    "folga_lateral": 50.0,        # entre tanque e tubo, para solda, pintura e inspecao
    "folga_sob_conteiner": 15.0,  # do topo da gaiola ao plano dos cantos (6 mm de flecha + 9)
    "baia_tecnica": 400.0,
    "chapas": {"fundo": 6.35, "lateral": 4.75, "tampa": 4.75},
    "niveis": {"alerta": 0.70, "alarme_alto": 0.80, "alarme_alto_alto": 0.90},
    "rho_efluente": 1000.0,
    "perna_solda": 5.0,           # filete entre tubos do quadro (parede de 6,35 mm), mm
    "perna_solda_travessa": 4.0,  # filete da travessa (parede de 4,75 mm) na longarina, mm
    # chapa do tanque nas travessas: filete intermitente dos dois lados da travessa
    "solda_chapa": {"perna": 3.0, "trecho": 50.0, "passo": 150.0},
    # Itens de detalhe: dimensoes INDICATIVAS para desenho e orcamento, a fechar com o
    # fabricante e com a planta do conteiner real. Nao entram nas verificacoes.
    "detalhes": {
        "chapa_topo": {"comp": 200.0, "larg": 180.0, "t": 19.0},   # sobre os montantes de canto
        # poco do pescador: caixa soldada sob o fundo, entre duas travessas inferiores
        "poco": {"comp": 300.0, "larg": 300.0, "prof": 80.0, "t": 6.35},
        "largura_escada": 1000.0,
        # olhal de icamento: chapa soldada na face de topo de cada montante de canto,
        # saindo do comprimento da base (como os acessorios do produto de serie)
        "olhal": {"alt": 120.0, "proj": 70.0, "t": 19.0, "furo": 28.0, "borda": 21.0,
                  "perna": 6.0},
        "calco": {"comp": 250.0, "larg": 200.0, "t": 12.5},     # um por montante, travado no piso
        "flange_succao": {"d": 220.0, "t": 16.0},
        "corrimao": {"d": 42.0, "alturas": (700.0, 920.0)},     # NBR 9050 6.9.2
        "cone": {"d": 60.0, "h": 40.0},        # cone de centragem / twistlock: item comercial
        "boca_inspecao": {"larg": 500.0, "alt": 300.0, "t": 9.5},  # flange cega na testa da baia
        "dn_succao": 100.0, "dn_lavagem": 32.0, "dn_entrada": 100.0, "n_entradas": 2,
    },
    "geracao_m3_por_turno": 1.57,  # memoria do cliente (REV.01, secao 6): 100 usuarios, 8 h
    # Vento - NBR 6123:2023. Local informado pelo usuario em 2026-10-12.
    "local": {
        "municipio": "Campos dos Goytacazes - RJ",
        # Figura 1: o municipio fica entre as isopletas de 30 e 35 m/s; vale a de cima.
        # Leitura de mapa: a conferir pelo responsavel tecnico.
        "v0": 35.0,
        "s1": 1.0,            # 5.2: terreno plano
        "categoria": "II",    # 5.3.1: terreno aberto, poucos obstaculos (a favor da seguranca)
        "classe": "A",        # 5.3.2: maior dimensao ate' 20 m
        "s3": 1.0,            # Tabela 4, grupo 3 (inclui estrutura desmontavel reutilizavel)
        # Figura 4 (baixa turbulencia), vento na lateral: o ponto cai entre as curvas de
        # 1,1 e 1,2; vale a de cima. O valor so' serve para as proporcoes em que foi lido.
        "ca": 1.2, "ca_lido_para": {"l1_l2": 2.48, "h_l1": 0.54},
    },
    # Apoio no terreno: a tensao admissivel e' dado de sondagem ou de prova de carga
    # (NBR 6122 7.3). Sem ela a memoria so' mostra cenarios, nao dimensiona.
    "apoio": {"tensao_admissivel_kPa": None, "cenarios_kPa": (100.0, 150.0, 200.0, 300.0)},
    "adotado": {
        "pressao_projeto_kPa": 5.0,      # sobrepressao E depressao de projeto do tanque
        "corrosao_mm": 1.0,              # descontado da espessura nas verificacoes de chapa
        "carga_canto_kN": 40.0,          # carga de servico maxima por canto (vai para a placa)
        "massa_conteiner_kg": 4000.0,    # estimativa p/ fundacao; conferir placa CSC e pesagem
        "sobrecarga_piso_kPa": 3.0,      # uso do sanitario; conferir na NBR 6120 Tabela 10
        "fator_dinamico_icamento": 2.0,
        # NBR 8261 4.6.3 admite parede 12,5 % mais fina que a nominal: as resistencias dos
        # tubos sao calculadas com essa espessura reduzida
        "fator_espessura_tubo": 0.875,
        # tara de um 1CC sem a transformacao (referencia de mercado): e' o conteiner MAIS
        # LEVE que pode estar em cima, usado so' na estabilidade ao vento. Conferir placa CSC.
        "massa_conteiner_minima_kg": 2200.0,
        "fator_peso_proprio_apoio": 1.05,   # peso da placa de apoio: 5 % da carga
        "angulo_cabo_icamento_graus": 60.0,   # minimo com a horizontal (pratica do produto de serie)
        "piso_conteiner_acima_dos_cantos_mm": 150.0,   # A MEDIR no conteiner real (define a escada)
        "k_perdas_respiro": 3.0,         # entrada + saida + 2 curvas + 4 m de tubo DN100
        "vazao_ar_caminhao_m3h": 325.0,  # bomba de vacuo tipica de limpa-fossa (275-325 m3/h)
        "d_respiro_mm": 100.0,
    },
}


def _ver(nome, sd, rd, unid, ref):
    return {"nome": nome, "sd": sd, "rd": rd, "unid": unid, "razao": sd / rd,
            "ok": sd <= rd, "ref": ref}


def tubo_de_calculo(spec, chave):
    """Propriedades do tubo com a parede reduzida (dimensoes externas e raio nominais)."""
    t = dict(spec[chave])
    f = spec["adotado"]["fator_espessura_tubo"]
    t["t"] = t["t"] * f
    prop = TB.tubo_retangular(t, raio_sobre_t=TB.RAIO_EXTERNO_MAX_SOBRE_T / f)
    prop["t_calculo_mm"] = t["t"]
    prop["massa_kg_m"] = TB.tubo_retangular(spec[chave])["massa_kg_m"]   # peso: parede nominal
    return prop


def geometria(spec):
    s, q = spec["skid"], spec["tubo_quadro"]
    ti, ts = spec["tubo_travessa_inf"], spec["tubo_travessa_sup"]
    ch = spec["chapas"]
    comp = s["comp"] - 2 * q["b"] - spec["folga_lateral"] - spec["baia_tecnica"]
    larg = s["larg"] - 2 * (q["b"] + spec["folga_lateral"])
    z_fundo = ti["h"]                                    # chapa de fundo sobre as travessas
    z_topo_gaiola = s["alt"] - spec["folga_sob_conteiner"]
    z_tampa = z_topo_gaiola - ts["h"]                    # tampa sob as travessas superiores
    alt_ext = z_tampa - z_fundo
    interno = (comp - 2 * ch["lateral"], larg - 2 * ch["lateral"],
               alt_ext - ch["fundo"] - ch["tampa"])
    vao_travessa = s["larg"] - 2 * q["b"]
    n_vaos = math.ceil(comp / spec["passo_travessa_max"])
    return {"tanque_ext": (comp, larg, alt_ext), "interno": interno,
            "z_fundo": z_fundo, "z_tampa": z_tampa, "z_topo_gaiola": z_topo_gaiola,
            "vao_travessa": vao_travessa, "passo": comp / n_vaos,
            "n_travessas": n_vaos + 1,
            "vao_longarina": (s["comp"] - q["h"]) / 2,   # entre eixos dos montantes
            "alt_montante": s["alt"]}


def capacidade(spec):
    c, l, h = geometria(spec)["interno"]
    v = c * l * h / 1e9
    niveis = {n: {"fracao": f, "volume_m3": v * f, "lamina_mm": h * f}
              for n, f in spec["niveis"].items()}
    v80 = niveis["alarme_alto"]["volume_m3"]
    return {"volume_m3": v, "niveis": niveis,
            "turnos_ate_alarme_alto": v80 / spec["geracao_m3_por_turno"]}


def massas(spec):
    g = geometria(spec)
    s, ch = spec["skid"], spec["chapas"]
    c, l, a = g["tanque_ext"]
    kg = lambda vol_mm3: vol_mm3 / 1e9 * TB.RHO_ACO
    quadro = TB.tubo_retangular(spec["tubo_quadro"])["massa_kg_m"]
    t_inf = TB.tubo_retangular(spec["tubo_travessa_inf"])["massa_kg_m"]
    t_sup = TB.tubo_retangular(spec["tubo_travessa_sup"])["massa_kg_m"]
    itens = {
        "chapa de fundo": kg(c * l * ch["fundo"]),
        "chapa da tampa": kg(c * l * ch["tampa"]),
        "chapas laterais": kg(2 * (c + l) * a * ch["lateral"]),
        "longarinas e testeiras (2 niveis)": 2 * 2 * (s["comp"] + s["larg"]) / 1000 * quadro,
        "montantes (6)": 6 * s["alt"] / 1000 * quadro,
        "travessas inferiores": g["n_travessas"] * g["vao_travessa"] / 1000 * t_inf,
        "travessas superiores": g["n_travessas"] * g["vao_travessa"] / 1000 * t_sup,
    }
    tanque = sum(v for k, v in itens.items() if k.startswith("chapa"))
    total = sum(itens.values())
    cap = capacidade(spec)
    return {"itens": itens, "tanque_kg": tanque, "aco_kg": total,
            "acessorios_kg": 0.10 * total,   # chapas de topo, conexoes, olhais: 10 % adotado
            "efluente_cheio_kg": cap["volume_m3"] * spec["rho_efluente"]}


def _faixa_chapa(nome, t_nom, vao, q_unif, q_tri, corr, ref):
    """Faixa de 1 mm de chapa, biapoiada no vao, regime elastico (W = t2/6)."""
    t = t_nom - corr
    m = q_unif * vao ** 2 / 8 + 0.0642 * q_tri * vao ** 2      # N.mm/mm
    sd = GAMA_Q * 6 * m / t ** 2
    v = _ver(nome, sd, FY_A36 / GA1, "MPa", ref)
    i = t ** 3 / 12
    v["flecha_mm"] = (5 * q_unif + 2.5 * q_tri) * vao ** 4 / (384 * E_ACO * i)
    v["t_calculo_mm"] = t
    return v


def chapas(spec):
    g, ad, ch = geometria(spec), spec["adotado"], spec["chapas"]
    p = ad["pressao_projeto_kPa"] / 1000                       # MPa
    h_int = g["interno"][2]
    p_liq = spec["rho_efluente"] * G * h_int / 1e9             # MPa no fundo, tanque cheio
    ref = "faixa biapoiada; NBR 8800 5.4 (fy/ga1, secao retangular em regime elastico)"
    return [
        _faixa_chapa("Tampa: pressao de projeto", ch["tampa"], g["passo"], p, 0.0,
                     ad["corrosao_mm"], ref),
        _faixa_chapa("Fundo: tanque cheio + sobrepressao", ch["fundo"], g["passo"],
                     p + p_liq, 0.0, ad["corrosao_mm"], ref),
        _faixa_chapa("Lateral: hidrostatica + sobrepressao", ch["lateral"],
                     g["tanque_ext"][2], p, p_liq, ad["corrosao_mm"], ref),
    ]


def barras(spec):
    g, ad = geometria(spec), spec["adotado"]
    m = massas(spec)
    fy = TB.FY_TUBO_RETANGULAR[spec["grau_tubo"]]
    quadro = tubo_de_calculo(spec, "tubo_quadro")
    trav = tubo_de_calculo(spec, "tubo_travessa_inf")
    trav_sup = tubo_de_calculo(spec, "tubo_travessa_sup")
    p = ad["pressao_projeto_kPa"] / 1000
    c, l, _ = g["tanque_ext"]
    h_int = g["interno"][2]
    p_liq = spec["rho_efluente"] * G * h_int / 1e9
    ref_m = "NBR 8800 5.4.2 (M_Rd = W.fy/ga1, limite elastico)"
    out = []

    # travessa inferior: liquido + sobrepressao (variaveis) + chapa de fundo e peso proprio
    lv = g["vao_travessa"]
    q_var = (p + p_liq) * g["passo"]                           # N/mm
    q_perm = (m["itens"]["chapa de fundo"] / (c / g["passo"]) * G / l
              + trav["massa_kg_m"] * G / 1000)                 # N/mm
    q_sd = GAMA_Q * q_var + GAMA_G * q_perm
    out.append(_ver("Travessa inferior: flexao", q_sd * lv ** 2 / 8 / 1e6,
                    trav["Wx_mm3"] * fy / GA1 / 1e6, "kN.m", ref_m))
    flecha = 5 * (q_var + q_perm) * lv ** 4 / (384 * E_ACO * trav["Ix_mm4"])
    out[-1]["flecha_mm"] = flecha
    out[-1]["vao_sobre_flecha"] = lv / flecha
    # operacao normal: tanque cheio, respiro aberto (sem sobrepressao)
    out[-1]["flecha_normal_mm"] = (5 * (p_liq * g["passo"] + q_perm) * lv ** 4
                                   / (384 * E_ACO * trav["Ix_mm4"]))
    r_trav_sd = q_sd * lv / 2                                  # N, reacao de calculo
    perna = spec["perna_solda_travessa"]
    lw = 2 * (spec["tubo_travessa_inf"]["h"] + spec["tubo_travessa_inf"]["b"])
    out.append(_ver("Travessa inferior: solda de filete no apoio", r_trav_sd / 1000,
                    0.6 * FW_E70 * 0.707 * perna * lw / GW2 / 1000, "kN",
                    "NBR 8800 Tabela 9 (0,60.Aw.fw/gw2)"))

    # travessa superior: so' a pressao de projeto sobre a tampa
    q_sd = GAMA_Q * p * g["passo"] + GAMA_G * trav_sup["massa_kg_m"] * G / 1000
    out.append(_ver("Travessa superior: flexao", q_sd * lv ** 2 / 8 / 1e6,
                    trav_sup["Wx_mm3"] * fy / GA1 / 1e6, "kN.m", ref_m))
    out[-1]["flecha_mm"] = 5 * p * g["passo"] * lv ** 4 / (384 * E_ACO * trav_sup["Ix_mm4"])

    # longarina inferior: viga continua de 2 vaos iguais, carga distribuida
    lg = g["vao_longarina"]
    w_var = m["efluente_cheio_kg"] * G / 2 / c                 # N/mm por longarina
    w_perm = ((m["tanque_kg"] + m["itens"]["travessas inferiores"]) * G / 2 / c
              + quadro["massa_kg_m"] * G / 1000)
    w_sd = GAMA_Q * w_var + GAMA_G * w_perm
    out.append(_ver("Longarina inferior, 6 apoios: flexao no apoio central",
                    w_sd * lg ** 2 / 8 / 1e6, quadro["Wx_mm3"] * fy / GA1 / 1e6,
                    "kN.m", ref_m))
    out[-1]["flecha_mm"] = (w_var + w_perm) * lg ** 4 / (185 * E_ACO * quadro["Ix_mm4"])
    # mesma longarina SEM os apoios do meio e com o tanque cheio: tem de reprovar
    # ou passar por conta, para a memoria dizer se o apoio central e' obrigatorio
    out.append(_ver("Longarina inferior, so' 4 cantos, tanque CHEIO",
                    w_sd * (2 * lg) ** 2 / 8 / 1e6, quadro["Wx_mm3"] * fy / GA1 / 1e6,
                    "kN.m", ref_m))
    out[-1]["informativo"] = True

    # longarina superior: reacoes das travessas superiores
    w_sd = (GAMA_Q * p * lv / 2 + GAMA_G * quadro["massa_kg_m"] * G / 1000)
    out.append(_ver("Longarina superior: flexao no montante central",
                    w_sd * lg ** 2 / 8 / 1e6, quadro["Wx_mm3"] * fy / GA1 / 1e6,
                    "kN.m", ref_m))

    # icamento vazio pelos 4 cantos superiores: so' a longarina inferior, sem contar a gaiola
    w_vazio = (m["aco_kg"] + m["acessorios_kg"]) * G / 2 / (2 * lg)
    w_sd = GAMA_G * ad["fator_dinamico_icamento"] * w_vazio
    out.append(_ver("Icamento vazio pelos 4 cantos: flexao da longarina",
                    w_sd * (2 * lg) ** 2 / 8 / 1e6, quadro["Wx_mm3"] * fy / GA1 / 1e6,
                    "kN.m", ref_m))

    # montante de canto: carga do conteiner com a excentricidade do centro do canto ISO
    q_t = spec["tubo_quadro"]
    area = quadro["A_mm2"]
    r_min = math.sqrt(quadro["Iy_mm4"] / area)
    lam0 = (g["alt_montante"] / r_min) / math.pi * math.sqrt(fy / E_ACO)
    n_rd = chi_compressao(lam0) * area * fy / GA1 / 1000       # kN
    ex = (spec["skid"]["comp"] - S_CANTOS) / 2 - q_t["h"] / 2  # mm, ao longo do comprimento
    ey = (spec["skid"]["larg"] - P_CANTOS) / 2 - q_t["b"] / 2
    mx_rd = quadro["Wx_mm3"] * fy / GA1 / 1e6
    my_rd = quadro["Wy_mm3"] * fy / GA1 / 1e6

    def interacao(n_sd):
        return n_sd / n_rd + n_sd * abs(ex) / 1000 / mx_rd + n_sd * abs(ey) / 1000 / my_rd

    n_placa = GAMA_Q * ad["carga_canto_kN"]
    out.append(_ver("Montante de canto: carga da placa (%.0f kN de servico)"
                    % ad["carga_canto_kN"], interacao(n_placa), 1.0, "-",
                    "NBR 8800 5.3 e 5.5 (interacao linear N + Mx + My)"))
    n_iso = 1.8 * R_ISO_1CC * G / 4 / 1000
    out.append(_ver("Montante de canto: envoltoria ISO (1,8 R / 4 = %.0f kN)" % n_iso,
                    interacao(n_iso), 1.0, "-",
                    "ISO 1496-1 5.3.4 e ISO 668 Tabela 2; NBR 8800 5.3 e 5.5"))
    out[-1]["informativo"] = True
    return {"verificacoes": out, "excentricidade_mm": (ex, ey), "N_Rd_kN": n_rd,
            "fy_tubo": fy, "lambda0": lam0}


def reacoes(spec):
    """Cargas de SERVICO em cada um dos 6 pontos de fundacao (kN)."""
    g, ad, m = geometria(spec), spec["adotado"], massas(spec)
    s = spec["skid"]
    base = (m["aco_kg"] + m["acessorios_kg"]) * G / 1000
    liq = m["efluente_cheio_kg"] * G / 1000
    cont = ad["massa_conteiner_kg"] * G / 1000
    uso = ad["sobrecarga_piso_kPa"] * s["comp"] * s["larg"] / 1e6
    # viga continua de 2 vaos: 3/16 em cada extremo, 10/16 no meio (por lado)
    dist = (base + liq) / 2
    canto = 0.1875 * dist + (cont + uso) / 4
    meio = 0.625 * dist
    return {"base_kN": base, "efluente_kN": liq, "conteiner_kN": cont, "uso_kN": uso,
            "total_kN": base + liq + cont + uso, "canto_kN": canto, "meio_kN": meio,
            "canto_placa_kN": 0.1875 * dist + ad["carga_canto_kN"]}


def vento(spec):
    """Forca de arrasto na lateral do conjunto base + conteiner - NBR 6123:2023, 4.2 e 4.3.3."""
    loc, s = spec["local"], spec["skid"]
    h = (s["alt"] + H_CONTEINER_1CC) / 1000                      # m
    if h > 5.0:
        raise ValueError("S2 so' esta' transcrito para z <= 5 m (altura do conjunto: %.2f m)" % h)
    l1, l2 = s["comp"] / 1000, s["larg"] / 1000                 # l1: face que recebe o vento
    lido = loc["ca_lido_para"]
    for nome, atual in (("l1_l2", l1 / l2), ("h_l1", h / l1)):
        if abs(atual / lido[nome] - 1) > 0.05:
            raise ValueError("Ca foi lido na Figura 4 para %s = %.2f; a geometria da' %.2f: "
                             "ler de novo" % (nome, lido[nome], atual))
    s2 = S2_ATE_5M[loc["categoria"]][loc["classe"]]
    vk = loc["v0"] * loc["s1"] * s2 * loc["s3"]
    q = 0.613 * vk ** 2 / 1000                                   # kPa
    pressao = q * loc["ca"]
    return {"h_m": h, "s2": s2, "vk_m_s": vk, "q_kPa": q, "pressao_kPa": pressao,
            "forca_conteiner_kN": pressao * l1 * H_CONTEINER_1CC / 1000,
            "forca_total_kN": pressao * l1 * h}


def estabilidade(spec):
    """Conjunto VAZIO e com o conteiner mais leve, vento na lateral (valores de calculo)."""
    v, ad, m = vento(spec), spec["adotado"], massas(spec)
    peso = (m["aco_kg"] + m["acessorios_kg"] + ad["massa_conteiner_minima_kg"]) * G / 1000
    h_sd = GAMA_VENTO * v["forca_total_kN"]
    braco = (spec["skid"]["larg"] - spec["tubo_quadro"]["b"]) / 2000   # ate' o eixo do montante
    tomb = _ver("Tombamento com o tanque vazio e o conteiner mais leve", h_sd * v["h_m"] / 2,
                0.9 * peso * braco, "kN.m",
                "equilibrio; vento da NBR 6123 com 1,4 e peso estabilizante com 0,9")
    return {"peso_minimo_kN": peso, "forca_horizontal_sd_kN": h_sd, "tombamento": tomb,
            # atrito que seria preciso entre o calco e o piso para o conjunto nao escorregar
            "atrito_necessario": h_sd / (0.9 * peso)}


def apoios(spec):
    """Carga de servico por apoio, pressao sob o calco e lado da placa de apoio no terreno."""
    r, v, ad = reacoes(spec), vento(spec), spec["adotado"]
    cal, ap = spec["detalhes"]["calco"], spec["apoio"]
    braco = (spec["skid"]["larg"] - spec["tubo_quadro"]["b"]) / 1000
    # o momento do vento desce pelos cantos do conteiner: dois cantos de cada lado
    vento_canto = v["forca_total_kN"] * v["h_m"] / 2 / braco / 2
    n_max = max(r["canto_placa_kN"] + vento_canto, r["meio_kN"])

    def lado(sigma_kpa):
        nec = math.sqrt(ad["fator_peso_proprio_apoio"] * n_max / sigma_kpa) * 1000
        return max(math.ceil(nec / 50.0) * 50.0, LADO_MIN_SAPATA)

    sigma = ap["tensao_admissivel_kPa"]
    return {"vento_canto_kN": vento_canto, "carga_max_kN": n_max,
            "pressao_calco_MPa": n_max * 1000 / (cal["comp"] * cal["larg"]),
            "cenarios": [(sg, lado(sg)) for sg in ap["cenarios_kPa"]],
            "tensao_admissivel_kPa": sigma, "lado_mm": lado(sigma) if sigma else None}


def respiro(spec):
    """Depressao no tanque quando o caminhao puxa AR pelo tanque (pescador descoberto)."""
    ad = spec["adotado"]
    area = math.pi * (ad["d_respiro_mm"] / 1000) ** 2 / 4

    def dp(q_m3h):
        v = q_m3h / 3600 / area
        return ad["k_perdas_respiro"] * 1.2 * v ** 2 / 2 / 1000, v     # kPa, m/s

    d, v = dp(ad["vazao_ar_caminhao_m3h"])
    p = ad["pressao_projeto_kPa"]
    q_lim = math.sqrt(p * 1000 * 2 / (ad["k_perdas_respiro"] * 1.2)) * area * 3600
    return {"depressao_kPa": d, "velocidade_m_s": v, "vazao_limite_m3h": q_lim,
            "verificacao": _ver("Respiro DN%.0f: depressao com %.0f m3/h de ar"
                                % (ad["d_respiro_mm"], ad["vazao_ar_caminhao_m3h"]),
                                d, p, "kPa", "perda de carga localizada (estimativa)")}


def _filete(perna, comprimento):
    """Forca resistente de calculo (kN) do filete - NBR 8800:2024 Tabela 9 (metal da solda)."""
    return 0.6 * FW_E70 * 0.707 * perna * comprimento / GW2 / 1000


def complementares(spec):
    """Verificacoes que a primeira emissao da REV.02 nao trazia."""
    g, ad, m = geometria(spec), spec["adotado"], massas(spec)
    fy = TB.FY_TUBO_RETANGULAR[spec["grau_tubo"]]
    q, ti = spec["tubo_quadro"], spec["tubo_travessa_inf"]
    quadro = tubo_de_calculo(spec, "tubo_quadro")
    trav = tubo_de_calculo(spec, "tubo_travessa_inf")
    p = ad["pressao_projeto_kPa"] / 1000
    c, l, _ = g["tanque_ext"]
    p_liq = spec["rho_efluente"] * G * g["interno"][2] / 1e9
    lv, lg = g["vao_travessa"], g["vao_longarina"]
    out = []

    def cortante_rd(t, prop):
        # NBR 8800 5.4.3.2: kv = 5, h = parte plana da alma, Aw = 2.h.tw
        tw = prop["t_calculo_mm"]
        h = t["h"] - 2 * prop["raio_externo_mm"]
        lam = h / tw
        lam_p, lam_r = (k * math.sqrt(5.0 * E_ACO / fy) for k in (1.10, 1.37))
        v_pl = 0.6 * 2 * h * tw * fy / GA1 / 1000
        if lam <= lam_p:
            return v_pl
        if lam <= lam_r:
            return lam_p / lam * v_pl
        return 1.24 * (lam_p / lam) ** 2 * v_pl

    # --- cortante ---
    q_perm = (m["itens"]["chapa de fundo"] / (c / g["passo"]) * G / l
              + trav["massa_kg_m"] * G / 1000)
    q_sd = GAMA_Q * (p + p_liq) * g["passo"] + GAMA_G * q_perm
    v_trav = q_sd * lv / 2 / 1000
    out.append(_ver("Travessa inferior: cortante", v_trav, cortante_rd(ti, trav), "kN",
                    "NBR 8800 5.4.3.2"))
    w_var = m["efluente_cheio_kg"] * G / 2 / c
    w_perm = ((m["tanque_kg"] + m["itens"]["travessas inferiores"]) * G / 2 / c
              + quadro["massa_kg_m"] * G / 1000)
    w_sd = GAMA_Q * w_var + GAMA_G * w_perm
    v_long = 0.625 * w_sd * lg / 1000            # viga continua de 2 vaos, no apoio central
    out.append(_ver("Longarina inferior: cortante no montante central", v_long,
                    cortante_rd(q, quadro), "kN", "NBR 8800 5.4.3.2"))

    # --- no' longarina-montante: filete em todo o contorno do tubo ---
    perna = spec["perna_solda"]
    lw = 2 * (q["h"] + q["b"])
    ref_solda = "NBR 8800 Tabela 9 (0,60.Aw.fw/gw2)"
    out.append(_ver("No' longarina-montante: solda, tanque cheio", v_long, _filete(perna, lw),
                    "kN", ref_solda))
    out.append(_ver("No' longarina-montante: parede do tubo ao cisalhamento", v_long,
                    0.6 * fy * quadro["t_calculo_mm"] * lw / GA1 / 1000, "kN",
                    "NBR 8800 6.5 (escoamento do metal-base)"))
    minimo = perna_minima(q["t"])         # tubo do quadro em tubo do quadro: mesma parede
    out.append(_ver("Perna minima do filete entre tubos do quadro", minimo, perna, "mm",
                    "NBR 8800 Tabela 11 (perna minima pela parte menos espessa)"))

    # --- icamento vazio pelos 4 cantos superiores ---
    vazio_n = (m["aco_kg"] + m["acessorios_kg"]) * G
    f_canto = GAMA_G * ad["fator_dinamico_icamento"] * vazio_n / 4 / 1000
    out.append(_ver("Icamento: solda do no' de canto a' tracao", f_canto, _filete(perna, lw),
                    "kN", ref_solda))
    ang = math.radians(ad["angulo_cabo_icamento_graus"])
    n_comp = f_canto / math.tan(ang)
    r_min = math.sqrt(quadro["Iy_mm4"] / quadro["A_mm2"])
    lam0 = (lg / r_min) / math.pi * math.sqrt(fy / E_ACO)
    out.append(_ver("Icamento: compressao na longarina superior (cabo a %.0f graus)"
                    % ad["angulo_cabo_icamento_graus"], n_comp,
                    chi_compressao(lam0) * quadro["A_mm2"] * fy / GA1 / 1000, "kN",
                    "NBR 8800 5.3"))
    out[-1]["ponto_de_icamento_kN"] = f_canto / math.sin(ang)

    # --- olhal de icamento: rasgamento, solda e flexao fora do plano ---
    ol = spec["detalhes"]["olhal"]
    f_cabo = f_canto / math.sin(ang)
    out.append(_ver("Olhal: rasgamento da chapa entre o furo e a borda", f_cabo,
                    2 * ol["borda"] * ol["t"] * 0.6 * 400.0 / 1.35 / 1000, "kN",
                    "NBR 8800 6.5 (ruptura por cisalhamento, fu = 400 MPa, ga2 = 1,35)"))
    out.append(_ver("Olhal: solda na face do montante", f_cabo,
                    _filete(ol["perna"], 2 * ol["alt"]), "kN", ref_solda))
    # cabos para um gancho central puxam o olhal tambem de lado (fora do plano da chapa)
    lateral = f_cabo * math.cos(ang) * (spec["skid"]["larg"] / 2) / math.hypot(
        spec["skid"]["larg"] / 2, spec["skid"]["comp"] / 2)
    sigma_ol = 6 * lateral * 1000 * (ol["proj"] / 2) / (ol["alt"] * ol["t"] ** 2)
    out.append(_ver("Olhal: flexao fora do plano (gancho central)", sigma_ol, FY_A36 / GA1,
                    "MPa", "NBR 8800 5.4 (fy/ga1, regime elastico)"))

    # --- chapa do tanque presa a's travessas: vacuo puxa a tampa, sobrepressao o fundo ---
    sc = spec["solda_chapa"]
    sd_linha = GAMA_Q * p * g["passo"]                       # N por mm de travessa
    rd_linha = (2 * 0.6 * FW_E70 * 0.707 * sc["perna"] / GW2) * sc["trecho"] / sc["passo"]
    out.append(_ver("Solda intermitente da chapa na travessa (vacuo)", sd_linha, rd_linha,
                    "N/mm", ref_solda))

    # --- chapa de topo: balanco alem do tubo, pressao uniforme sob a chapa ---
    ct = spec["detalhes"]["chapa_topo"]
    n_sd = GAMA_Q * ad["carga_canto_kN"] * 1000
    pressao = n_sd / (ct["comp"] * ct["larg"])
    balanco = max(ct["comp"] - q["h"], ct["larg"] - q["b"])
    sigma = 6 * (pressao * balanco ** 2 / 2) / ct["t"] ** 2
    out.append(_ver("Chapa de topo: flexao do balanco de %.0f mm" % balanco, sigma,
                    FY_A36 / GA1, "MPa", "NBR 8800 5.4 (fy/ga1, regime elastico)"))

    # --- forca horizontal do conteiner (vento) passando pelos 4 montantes de canto ---
    h_sd = GAMA_VENTO * vento(spec)["forca_conteiner_kN"]
    livre = (g["z_topo_gaiola"] - q["h"]) - q["h"]                  # montante entre longarinas
    m_sd = h_sd / 4 * livre / 2 / 1000                              # kN.m, dupla curvatura
    my_rd = quadro["Wy_mm3"] * fy / GA1 / 1e6
    r_min_m = math.sqrt(quadro["Iy_mm4"] / quadro["A_mm2"])
    lam0_m = (g["alt_montante"] / r_min_m) / math.pi * math.sqrt(fy / E_ACO)
    n_rd = chi_compressao(lam0_m) * quadro["A_mm2"] * fy / GA1
    n_placa = GAMA_Q * ad["carga_canto_kN"] * 1000
    out.append(_ver("Montante de canto: vento lateral + carga da placa",
                    n_placa / n_rd + m_sd / my_rd, 1.0, "-",
                    "NBR 8800 5.5 (interacao linear); vento da NBR 6123:2023"))
    out.append(estabilidade(spec)["tombamento"])

    # --- poco do pescador cabe sob o fundo, entre duas travessas ---
    pc = spec["detalhes"]["poco"]
    out.append(_ver("Poco do pescador: profundidade sob o fundo", pc["prof"] + pc["t"],
                    ti["h"] - 10.0, "mm", "geometria (10 mm livres ate' o terreno)"))
    out.append(_ver("Poco do pescador: comprimento entre travessas", pc["comp"],
                    g["passo"] - ti["b"] - 40.0, "mm", "geometria (20 mm de cada lado)"))
    return out


def acesso(spec):
    """Degraus ate' o piso do conteiner - NBR 9050:2020, 6.8.2."""
    desnivel = spec["skid"]["alt"] + spec["adotado"]["piso_conteiner_acima_dos_cantos_mm"]
    n = math.ceil(desnivel / ESPELHO_MAX)
    e = desnivel / n
    piso = min(max(640.0 - 2 * e, PISO_MIN), PISO_MAX)
    return {"desnivel_mm": desnivel, "espelhos": n, "espelho_mm": e, "piso_mm": piso,
            "p_mais_2e_mm": piso + 2 * e,
            "ok": ESPELHO_MIN <= e <= ESPELHO_MAX and 630.0 <= piso + 2 * e <= 650.0}


def juntas_soldadas(spec):
    """Tabela de soldas: (junta, tipo, perna mm, quantidade, comprimento de cada, obs)."""
    g, det = geometria(spec), spec["detalhes"]
    q, ti = spec["tubo_quadro"], spec["tubo_travessa_inf"]
    c, l, a = g["tanque_ext"]
    sc = spec["solda_chapa"]
    n = lambda x: ("%.0f" % x)
    estanque = "CONTINUA, ESTANQUE"
    return [
        ("Longarina e testeira no montante", "FILETE EM TODO O CONTORNO", spec["perna_solda"],
         24, 2 * (q["h"] + q["b"]), "AWS D1.1"),
        ("Travessa na longarina", "FILETE EM TODO O CONTORNO", spec["perna_solda_travessa"],
         4 * g["n_travessas"], 2 * (ti["h"] + ti["b"]), "AWS D1.1"),
        ("Chapa de topo no montante de canto", "FILETE EM TODO O CONTORNO", spec["perna_solda"],
         4, 2 * (q["h"] + q["b"]), ""),
        ("Olhal de icamento no montante", "FILETE DOS DOIS LADOS", det["olhal"]["perna"],
         4, 2 * det["olhal"]["alt"], "INSPECAO POR LIQUIDO PENETRANTE"),
        ("Fundo nas laterais e testas", "FILETE DOS DOIS LADOS, " + estanque, 4, 1,
         2 * (c + l), "LIQUIDO PENETRANTE NOS CANTOS"),
        ("Lateral na testa (cantos verticais)", "FILETE DOS DOIS LADOS, " + estanque, 4, 4,
         a, "LIQUIDO PENETRANTE"),
        ("Tampa nas laterais e testas (fechamento)", "FILETE EXTERNO, " + estanque, 4, 1,
         2 * (c + l), "ULTIMA SOLDA DO TANQUE"),
        ("Poco do pescador no fundo", "FILETE DOS DOIS LADOS, " + estanque, 4, 1,
         2 * (det["poco"]["comp"] + det["poco"]["larg"]), "LIQUIDO PENETRANTE"),
        ("Bocais e luvas na chapa", "FILETE DOS DOIS LADOS, " + estanque, 4,
         5 + det["n_entradas"], math.pi * det["dn_succao"], "LIQUIDO PENETRANTE"),
        ("Chapa do tanque nas travessas", "FILETE INTERMITENTE %s A CADA %s, DOIS LADOS"
         % (n(sc["trecho"]), n(sc["passo"])), sc["perna"], 2 * g["n_travessas"],
         g["tanque_ext"][1], "NA TAMPA: ANTES DA PINTURA INTERNA"),
    ]


def componentes(spec):
    """Itens comprados: (item, especificacao, quantidade)."""
    det, ad = spec["detalhes"], spec["adotado"]
    n = lambda x: ("%.0f" % x)
    return [
        ("Valvula de esfera flangeada", "DN%s (4 pol.), corpo em latao ou inox, na succao"
         % n(det["dn_succao"]), 1),
        ("Engate rapido", "DN%s, modelo do operador do caminhao de succao"
         % n(det["dn_succao"]), 1),
        ("Tubo de succao e pescador", "DN%s, aco-carbono, com flange soldado"
         % n(det["dn_succao"]), 1),
        ("Luva com tampao para lavagem", "DN%s, com engate de mangueira" % n(det["dn_lavagem"]), 1),
        ("Tubo de respiro", "DN%s, com terminal e tela acima da cobertura"
         % n(ad["d_respiro_mm"]), 1),
        ("Valvula quebra-vacuo", "abertura total ate %.1f kPa de depressao, em derivacao no respiro"
         % (ad["pressao_projeto_kPa"] / 2), 1),
        ("Transmissor de nivel hidrostatico", "0 a 1 m de coluna, para esgoto, saida 4-20 mA", 1),
        ("Chave de nivel alto-alto", "independente do transmissor, na cota de 90 %", 1),
        ("Cone de centragem ou twistlock", "compativel com canto ISO 1161", 4),
        ("Tampa da boca de inspecao", "%s x %s mm, flange cega com junta de borracha "
         "(unico item aparafusado)" % (n(det["boca_inspecao"]["larg"]),
                                       n(det["boca_inspecao"]["alt"])), 1),
        ("Calco de nivelamento", "chapa %s x %s x %s mm, sob cada montante, travada no piso" % (
            n(det["calco"]["comp"]), n(det["calco"]["larg"]),
            ("%.1f" % det["calco"]["t"]).replace(".", ",")), 6),
        ("Placa de identificacao", "inox gravado, rebitada na testeira traseira", 1),
    ]


def notas_gerais(spec):
    ad, cap = spec["adotado"], capacidade(spec)
    f = lambda x, c=1: ("%.*f" % (c, x)).replace(".", ",")
    return [
        "1. Tubos NBR 8261 grau %s. Chapas ASTM A36. Eletrodo ou arame classe E70." % spec["grau_tubo"],
        "2. Tudo soldado. Unico item aparafusado: a tampa da boca de inspecao.",
        "3. Soldas do tanque continuas e estanques, conforme a tabela. Procedimento AWS D1.1.",
        "4. Inspecao visual em 100 % das soldas; liquido penetrante (NBR NM 334) onde a tabela indica.",
        "5. SEQUENCIA: (a) gaiola inferior; (b) fundo, laterais, testas, poco e bocais; "
        "(c) jato e pintura interna;",
        "   (d) tampa ja' soldada nas travessas superiores e pintada por baixo, com 30 mm sem tinta "
        "nas bordas;",
        "   (e) solda de fechamento da tampa por fora; (f) retoque interno pela boca de inspecao; "
        "(g) ensaio.",
        "6. Ensaio de estanqueidade com agua ate' 0,5 m acima da tampa, sobre os 6 apoios, por 24 h.",
        "7. Pintura interna para imersao em esgoto (ISO 12944-5, Tabela C.6). Externa conforme "
        "o local (ISO 12944-2).",
        "8. Fechar com tampao soldado toda ponta aberta de tubo.",
        "9. Pressao de projeto do tanque: +/- %s kPa. Volume cheio %s m3; operacional (80 %%) %s m3."
        % (f(ad["pressao_projeto_kPa"]), f(cap["volume_m3"], 2),
           f(cap["niveis"]["alarme_alto"]["volume_m3"], 2)),
        "10. Carga maxima de servico por canto: %s kN. APOIAR EM 6 PONTOS, TRAVADOS NO PISO "
        "CONTRA O VENTO." % f(ad["carga_canto_kN"], 0),
        "11. ICAR E TRANSPORTAR SOMENTE VAZIO, pelos 4 olhais, cabos a no minimo %s graus "
        "da horizontal." % f(ad["angulo_cabo_icamento_graus"], 0),
        "12. Conferir no conteiner real, antes do corte: medidas, cantos, porta, shaft do respiro "
        "e passagens de esgoto.",
        "13. Dimensoes em milimetros. Nao medir no desenho.",
    ]


def calcular(spec=None):
    spec = spec or SPEC_REV02
    b = barras(spec)
    r = respiro(spec)
    ver = chapas(spec) + b["verificacoes"] + [r["verificacao"]]
    # flechas em servico contra o limite de viga de piso
    lv, lg = geometria(spec)["vao_travessa"], geometria(spec)["vao_longarina"]
    trav = [v for v in ver if v["nome"] == "Travessa inferior: flexao"][0]
    long_ = [v for v in ver if "6 apoios" in v["nome"]][0]
    ref_f = "NBR 8800 Tabela B.1 (viga de piso, vao/%.0f)" % FLECHA_LIMITE_BARRA
    ver.append(_ver("Travessa inferior: flecha, tanque cheio", trav["flecha_normal_mm"],
                    lv / FLECHA_LIMITE_BARRA, "mm", ref_f))
    ver.append(_ver("Longarina inferior: flecha, tanque cheio", long_["flecha_mm"],
                    lg / FLECHA_LIMITE_BARRA, "mm", ref_f))
    ver += complementares(spec)
    return {"spec": spec, "geometria": geometria(spec), "capacidade": capacidade(spec),
            "massas": massas(spec), "barras": b, "reacoes": reacoes(spec), "respiro": r,
            "vento": vento(spec), "estabilidade": estabilidade(spec), "apoios": apoios(spec),
            "acesso": acesso(spec), "juntas": juntas_soldadas(spec),
            "componentes": componentes(spec), "notas": notas_gerais(spec),
            "verificacoes": ver,
            "aprovado": all(v["ok"] for v in ver if not v.get("informativo"))}


if __name__ == "__main__":
    res = calcular()
    print("interno", [round(x, 1) for x in res["geometria"]["interno"]],
          "passo %.0f" % res["geometria"]["passo"], "n_trav", res["geometria"]["n_travessas"])
    print("volume %.2f m3; 80%% = %.2f m3; turnos %.1f" % (
        res["capacidade"]["volume_m3"],
        res["capacidade"]["niveis"]["alarme_alto"]["volume_m3"],
        res["capacidade"]["turnos_ate_alarme_alto"]))
    print("aco %.0f kg" % res["massas"]["aco_kg"], {k: round(v) for k, v in res["massas"]["itens"].items()})
    for v in res["verificacoes"]:
        print("%-62s %8.2f / %8.2f %-5s %.2f %s%s" % (
            v["nome"], v["sd"], v["rd"], v["unid"], v["razao"], "OK" if v["ok"] else "NAO",
            " (informativo)" if v.get("informativo") else ""))
    print({k: round(v, 1) for k, v in res["reacoes"].items()})
    print({k: round(v, 2) for k, v in res["respiro"].items() if k != "verificacao"})
    print({k: round(v, 3) for k, v in res["vento"].items()})
    print({k: round(v, 2) for k, v in res["estabilidade"].items() if k != "tombamento"})
    print(res["apoios"])
    print("APROVADO" if res["aprovado"] else "REPROVADO")
