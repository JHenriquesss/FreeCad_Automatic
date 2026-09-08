# ============================================================================
# madeira_nbr7190.py - MADEIRA SERRADA PELA NBR 7190-1:2022 (G66)
#
# FONTE (lida na pagina, nao de memoria):
#   fontes/15_MADEIRA/MADEIRA__NBR__NBR-7190-2022-PARTES-1-A-7__projeto-
#   estruturas-madeira-completa.pdf (F136, 249 pp, com camada de texto).
#   Parte 1 (pp.1-81 do PDF): criterios de dimensionamento. Notebook 15
#   ("FreeCAD Automatic - 15 Estruturas de Madeira").
#   A Parte 1 e' autocontida para o que este modulo implementa: Tab.1
#   (umidade, p.10), Tab.3 (pecas estruturais, p.12), kmod (5.8.4, p.14),
#   gamma_w (5.8.5), resistencias de calculo (6.2.6), tracao (6.3.2),
#   compressao (6.3.3), flexao (6.3.4), cisalhamento (6.4.2), estabilidade
#   (6.5.3-6.5.5), apoio perpendicular (6.3.3 + 6.2.4 Tab.6), embutimento
#   (6.2.5), pino (7.1.4), grupo (7.1.7), madeira-aco 7.3 (modos a-l),
#   espacamentos Tab.14 (7.1.10), ELS 8 (flecha + fluencia Tab.20/21).
#
# NUCLEO IMPLEMENTADO (secao citada em cada conta):
#   - classe de resistencia DECLARADA da Tab.3, sem default em assinatura
#     nenhuma (a regra do SPT do G9: sem ensaio nao ha numero). "D20" e'
#     classe de corpo-de-prova (Tab.2, NBR 7190-3) e e' RECUSADA com o
#     endereco; nomes comuns as duas tabelas (D30/D40/D50/D60) valem pela
#     Tab.3, e isso fica dito no resultado.
#   - kmod = kmod1 . kmod2 (5.8.4): kmod1 pela classe de carregamento
#     (Tab.4) e kmod2 pela classe de umidade (Tab.5), na coluna da
#     categoria (serrada/rolica x recomposta). MLC, MLCC e LVL tem coluna
#     propria na norma mas sao OUTRO LOTE (fora do escopo do G66) e sao
#     recusados com motivo, em vez de cairem na coluna errada.
#   - fd = kmod . fk / gamma_w (6.2.6), gamma_w = 1,4 (tensoes normais) e
#     1,8 (cisalhamento) no ELU (5.8.5), 1,0 no ELS (5.8.6).
#   - tracao paralela (6.3.2, area liquida), compressao paralela (6.3.3)
#     COM estabilidade (6.5: lambda <= 140, lambda_rel, kc com betac = 0,2
#     para serrada/rolica), flexao simples reta (6.3.4) com a borda
#     comprimida CONTIDA (travamento declarado; 6.5.6 fora do lote),
#     cisalhamento longitudinal retangular 1,5.V/A (6.4.2),
#     flexocompressao reta (6.3.7 quadratica + 6.5.5), apoio com
#     compressao perpendicular (fc90,d = 0,25.fc0,d.alfa_n, alfa_n da
#     Tab.6 com interpolacao), Hankinson acima de 6 graus (6.2.8),
#     tracao perpendicular localizada no no (F90, 7.1.1).
#   - ligacao com CHAPA DE ACO + pinos (7.3, modos a-l legiveis) com
#     embutimento (6.2.5/7.1.3), My,k = 0,3.fu.d^2,6 (7.1.4), grupo
#     (7.1.7), Rd = kmod1.kmod2.Rk/1,4 com kmod1 <= 1 no aco (7.1.2) e
#     geometria minima (7.2 a-f, 7.1.9). Efeito corda sem ensaio = 0
#     (conservador, dito). Madeira-madeira (7.2), aneis (7.4) e chapas
#     com dentes (7.5, so fabricante) seguem fora do lote, nomeados em
#     escopo() com motivo e endereco.
#   - ELS da terca (8): flecha instantanea com E0,med, fluencia phi da
#     Tab.20, limites da Tab.21 para viga biapoiada sem forro fragil
#     (a Tab.21 da FAIXA: sem declaracao vale o extremo estrito -
#     inst L/500, fin L/300, net,fin L/350); com forro fragil o limite
#     da variavel (L/500 e 15 mm) tambem e' verificado.
#
# FRONTEIRA DO PESO (a laje do G52 outra vez): este modulo SOMA ZERO de
# peso proprio por dentro - recebe Nd pronto. O peso proprio da madeira
# entra pela via da CARGA (quem chama lanca rho da Tab.3 x volume), e a
# igualdade mora no gate de fechamento de quem chama.
#
# Unidades: m, kN; resistencias em kN/m2 (MPa x 1000); pinos em mm/N.
# STATELESS, puro (so math).
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Madeira serrada pela NBR 7190-1:2022: classes Tab.3, kmod, verificacoes
de barra (tracao, compressao com estabilidade, flexao, cisalhamento,
flexocompressao, apoio), ligacao madeira-aco com pinos (7.3) e ELS de
flecha. Classe e categoria sao entradas declaradas, sem default."""

from __future__ import annotations

import math

FONTE = ("ABNT NBR 7190-1:2022 Parte 1, F136 "
         "(fontes/15_MADEIRA, notebook 15)")


class EntradaMadeira(ValueError):
    """A entrada declarada nao descreve madeira que este modulo calcule."""


# --- Tab.3: classes de pecas estruturais (fb,k ft0,k ft90,k fc0,k fc90,k
# --- fv,k em MPa; E em GPa; rho em kg/m3). Transcrita da p.12 do PDF.
_T3_CONIFERAS = {
    "C14": (14, 8, 0.4, 16, 2.0, 3.0, 7, 4.7, 0.20, 0.40, 290, 350),
    "C16": (16, 10, 0.4, 17, 2.2, 3.2, 8, 5.4, 0.30, 0.50, 310, 370),
    "C18": (18, 11, 0.4, 18, 2.2, 3.4, 9, 6.0, 0.30, 0.60, 320, 380),
    "C20": (20, 12, 0.4, 19, 2.3, 3.6, 9.5, 6.4, 0.30, 0.60, 330, 390),
    "C22": (22, 13, 0.4, 20, 2.4, 3.8, 10, 6.7, 0.30, 0.60, 340, 410),
    "C24": (24, 14, 0.4, 21, 2.5, 4.0, 11, 7.4, 0.40, 0.70, 350, 420),
    "C27": (27, 16, 0.4, 22, 2.6, 4.0, 12, 7.7, 0.40, 0.70, 370, 450),
    "C30": (30, 18, 0.4, 23, 2.7, 4.0, 12, 8.0, 0.40, 0.80, 380, 460),
    "C35": (35, 21, 0.4, 25, 2.8, 4.0, 13, 8.7, 0.40, 0.80, 400, 480),
    "C40": (40, 24, 0.4, 26, 2.9, 4.0, 14, 9.4, 0.50, 0.90, 420, 500),
    "C45": (45, 27, 0.4, 27, 3.1, 4.0, 15, 10.0, 0.50, 0.90, 440, 520),
    "C50": (50, 30, 0.4, 29, 3.2, 4.0, 16, 11.0, 0.50, 1.00, 460, 550),
}
_T3_FOLHOSAS = {
    "D18": (18, 11, 0.6, 18, 7.5, 3.4, 9.5, 8.0, 0.60, 0.60, 475, 570),
    "D24": (24, 14, 0.6, 21, 7.8, 4.0, 10, 8.5, 0.70, 0.60, 485, 580),
    "D30": (30, 18, 0.6, 23, 8.0, 4.0, 11, 9.2, 0.70, 0.70, 530, 640),
    "D35": (35, 21, 0.6, 25, 8.1, 4.0, 12, 10.0, 0.80, 0.80, 540, 650),
    "D40": (40, 24, 0.6, 26, 8.3, 4.0, 13, 11.0, 0.90, 0.80, 560, 660),
    "D50": (50, 30, 0.6, 29, 9.3, 4.0, 14, 12.0, 0.90, 0.90, 620, 750),
    "D60": (60, 36, 0.6, 32, 11.0, 4.5, 17, 14.0, 1.10, 1.10, 700, 840),
    "D70": (70, 42, 0.6, 34, 13.5, 5.0, 20, 16.8, 1.33, 1.25, 900, 1080),
}

_CHAVES_T3 = ("fbk_MPa", "ft0k_MPa", "ft90k_MPa", "fc0k_MPa", "fc90k_MPa",
              "fvk_MPa", "E0m_GPa", "E005_GPa", "E90m_GPa", "Gm_GPa",
              "rhok", "rhom")

CLASSES_TABELA_3 = tuple(list(_T3_CONIFERAS) + list(_T3_FOLHOSAS))

# Classes que so existem na Tab.2 (corpo-de-prova, NBR 7190-3): recusadas
# com o endereco da Parte 3, em vez de herdarem numero da Tab.3.
CLASSES_SOMENTE_TAB2 = ("D20",)

CATEGORIAS = ("serrada", "rolica", "recomposta")

# Materiais com coluna propria na norma mas fora deste lote (G66).
MATERIAIS_FORA_DO_LOTE = ("MLC", "MLCC", "LVL", "CLT", "compensado", "OSB")

# Tab.4 (5.8.4.1): kmod1 por classe de carregamento x grupo de material.
# "serrada" cobre serrada/rolica/MLC/MLCC/LVL (primeira coluna); a segunda
# coluna e' a da madeira recomposta. MLC/MLCC/LVL sao recusados acima, mas
# a coluna e' a mesma da serrada - sem numero novo.
KMOD1 = {
    "permanente": {"serrada": 0.60, "recomposta": 0.30},
    "longa": {"serrada": 0.70, "recomposta": 0.45},
    "media": {"serrada": 0.80, "recomposta": 0.65},
    "curta": {"serrada": 0.90, "recomposta": 0.90},
    "instantanea": {"serrada": 1.10, "recomposta": 1.10},
}
CLASSES_CARREGAMENTO = tuple(KMOD1)

# Tab.5 (5.8.4.2): kmod2 por classe de umidade (Tab.1) x grupo.
KMOD2 = {
    1: {"serrada": 1.00, "recomposta": 1.00},
    2: {"serrada": 0.90, "recomposta": 0.95},
    3: {"serrada": 0.80, "recomposta": 0.93},
    4: {"serrada": 0.70, "recomposta": 0.90},
}
CLASSES_UMIDADE = (1, 2, 3, 4)

GAMMA_W_NORMAL = 1.4   # ELU, tensoes normais (5.8.5)
GAMMA_W_CISALHAMENTO = 1.8  # ELU, cisalhamento (5.8.5)
GAMMA_W_ELS = 1.0      # ELS (5.8.6)
GAMMA_LIG = 1.4        # ligacao (7.1.2)

LAMBDA_MAX = 140  # 6.5.3: esbeltez limite de peca comprimida
BETA_C_MACICA = 0.2  # 6.5.5: serrada e rolica

# Tab.6 (6.2.4): alfa_n pela extensao do carregamento (cm). Interpolacao
# linear fora dos pontos; extremos fixos (a <= 7,5 cm ou a >= 15 cm => 1).
_ALFA_N = ((1.0, 2.00), (2.0, 1.70), (3.0, 1.55), (4.0, 1.40), (5.0, 1.30),
           (7.5, 1.15), (10.0, 1.10), (15.0, 1.00))

# Tab.20 (8.1): fluencia phi da serrada/rolica por classe de umidade.
FLUENCIA_SERRADA = {1: 0.6, 2: 0.8, 3: 0.8, 4: 2.0}


def _grupo(categoria):
    if categoria in ("serrada", "rolica"):
        return "serrada"
    if categoria == "recomposta":
        return "recomposta"
    raise EntradaMadeira(
        "categoria %r fora do lote (use %s; %s exigem Parte 1 alem da "
        "serrada e dimensionamento proprio)"
        % (categoria, " ou ".join(CATEGORIAS),
           ", ".join(MATERIAIS_FORA_DO_LOTE)))


def propriedades_classe(classe):
    """Propriedades caracteristicas da classe Tab.3 (6.2.6: valores a 12 %).

    Devolve dict com resistencias em kN/m2, E em kN/m2 e rho em kg/m3,
    mais `conifera` (True para C*, False para D*) e a nota de que nomes
    comuns as Tabs.2/3 valem pela Tab.3 (pecas estruturais, NBR 7190-4).
    Sem default: classe ausente RECUSA (regra do SPT do G9)."""
    if not isinstance(classe, str):
        raise EntradaMadeira("classe de resistencia deve ser declarada "
                             "(Tab.3: %s)" % ", ".join(CLASSES_TABELA_3))
    sigla = classe.strip().upper()
    if sigla in CLASSES_SOMENTE_TAB2:
        raise EntradaMadeira(
            "classe %s e' de corpo-de-prova isento de defeitos (Tab.2, "
            "NBR 7190-3 Tab.A.1 de especies nativas): declare a classe da "
            "PECA estrutural (Tab.3, NBR 7190-4)" % sigla)
    if sigla in _T3_CONIFERAS:
        vals = _T3_CONIFERAS[sigla]
        conifera = True
    elif sigla in _T3_FOLHOSAS:
        vals = _T3_FOLHOSAS[sigla]
        conifera = False
    else:
        raise EntradaMadeira(
            "classe %r desconhecida na Tab.3 (coniferas %s; folhosas %s)"
            % (classe, ", ".join(_T3_CONIFERAS), ", ".join(_T3_FOLHOSAS)))
    prop = dict(zip(_CHAVES_T3, vals))
    prop["classe"] = sigla
    prop["conifera"] = conifera
    prop["tabela"] = "7190-1 Tab.3 (pecas estruturais)"
    if sigla in ("D30", "D40", "D50", "D60"):
        prop["nota_tabela"] = ("nome comum as Tabs.2/3: vale a Tab.3 "
                               "(peca estrutural)")
    # kN/m2 (MPa x 1000) e E em kN/m2 (GPa x 1e6).
    for chave in ("fbk_MPa", "ft0k_MPa", "ft90k_MPa", "fc0k_MPa",
                  "fc90k_MPa", "fvk_MPa"):
        prop[chave.replace("_MPa", "_d0")] = prop[chave] * 1000.0
    for chave in ("E0m_GPa", "E005_GPa", "E90m_GPa", "Gm_GPa"):
        prop[chave.replace("_GPa", "")] = prop[chave] * 1e6
    return prop


def kmod(classe_carregamento, classe_umidade, categoria="serrada"):
    """kmod = kmod1 . kmod2 (5.8.4). Tudo declarado, sem default."""
    grupo = _grupo(categoria)
    if classe_carregamento not in KMOD1:
        raise EntradaMadeira(
            "classe de carregamento %r invalida (Tab.4: %s)"
            % (classe_carregamento, ", ".join(CLASSES_CARREGAMENTO)))
    try:
        umidade = int(classe_umidade)
    except (TypeError, ValueError):
        raise EntradaMadeira(
            "classe de umidade deve ser 1-4 (Tab.1)") from None
    if umidade not in KMOD2:
        raise EntradaMadeira(
            "classe de umidade %r invalida (Tab.1: 1-4)" % (classe_umidade,))
    k1 = KMOD1[classe_carregamento][grupo]
    k2 = KMOD2[umidade][grupo]
    return {"kmod": round(k1 * k2, 4), "kmod1": k1, "kmod2": k2,
            "classe_carregamento": classe_carregamento,
            "classe_umidade": umidade, "categoria": categoria,
            "fonte": FONTE}


def resistencias_calculo(prop, kmod_num, gamma_w=GAMMA_W_NORMAL):
    """fd por solicitacao (6.2.6): tracao/flexao/compressao com gamma_w e
    cisalhamento com 1,8. `kmod_num` e' o numero (saida de kmod())."""
    k = float(kmod_num)
    return {
        "ft0d": k * prop["ft0k_d0"] / gamma_w,
        "fc0d": k * prop["fc0k_d0"] / gamma_w,
        "fmd": k * prop["fbk_d0"] / gamma_w,
        "fv0d": k * prop["fvk_d0"] / GAMMA_W_CISALHAMENTO,
        "fc90d_base": k * prop["fc90k_d0"] / gamma_w,
        "kmod": k, "gamma_w": gamma_w, "fonte": FONTE,
    }


# --- verificacoes de barra -------------------------------------------------
def verifica_tracao(Nd_kN, A_liq_m2, ft0d):
    """6.3.2: sigma = Nd/A_liq <= ft0,d."""
    if A_liq_m2 <= 0:
        raise EntradaMadeira("area liquida deve ser > 0")
    sigma = abs(float(Nd_kN)) / A_liq_m2
    util = sigma / ft0d if ft0d > 0 else float("inf")
    return {"solicitacao": "tracao_paralela_6.3.2", "sigma_kNm2": sigma,
            "resistencia_kNm2": ft0d, "util": util, "OK": bool(util <= 1.0)}


def esbeltez(L0_m, I_m4, A_m2):
    """lambda = L0/sqrt(I/A) (6.5.3)."""
    if A_m2 <= 0 or I_m4 <= 0 or L0_m < 0:
        raise EntradaMadeira("L0/I/A devem ser positivos para esbeltez")
    i = math.sqrt(I_m4 / A_m2)
    return L0_m / i if i > 0 else float("inf")


def esbeltez_relativa(lam, fc0k_kNm2, E005_kNm2):
    """lambda_rel = lambda/pi . sqrt(fc0,k/E0,05) (6.5.4)."""
    return lam / math.pi * math.sqrt(fc0k_kNm2 / E005_kNm2)


def coef_flambagem(lam_rel, betac=BETA_C_MACICA):
    """kc de 6.5.5 (kx/ky): k = 0,5[1+betac(lam_rel-0,3)+lam_rel^2]."""
    k = 0.5 * (1.0 + betac * (lam_rel - 0.3) + lam_rel ** 2)
    disc = k * k - lam_rel ** 2
    kc = 1.0 / (k + math.sqrt(max(disc, 0.0)))
    return {"kc": kc, "k": k, "lam_rel": lam_rel}


def verifica_compressao(Nd_kN, A_m2, fc0d, lam, fc0k, E005):
    """6.3.3 + 6.5: resistencia (sigma <= fc0,d) E estabilidade
    (sigma <= kc.fc0,d, com lam_rel; dispensa abaixo de 0,3)."""
    if A_m2 <= 0:
        raise EntradaMadeira("area deve ser > 0")
    sigma = abs(float(Nd_kN)) / A_m2
    util_res = sigma / fc0d if fc0d > 0 else float("inf")
    lam_rel = esbeltez_relativa(lam, fc0k, E005)
    detalhe = {"solicitacao": "compressao_paralela_6.3.3+6.5",
               "sigma_kNm2": sigma, "fc0d_kNm2": fc0d,
               "lambda": lam, "lambda_rel": lam_rel,
               "lambda_ok": bool(lam <= LAMBDA_MAX),
               "util_resistencia": util_res}
    if lam > LAMBDA_MAX:
        detalhe.update({"OK": False, "kc": None,
                        "motivo": "lambda %.1f > 140 (6.5.3)" % lam})
        return detalhe
    if lam_rel <= 0.3:
        detalhe.update({"kc": 1.0, "estabilidade": "dispensada_6.5.5",
                        "util": util_res, "OK": bool(util_res <= 1.0)})
        return detalhe
    kc = coef_flambagem(lam_rel)["kc"]
    util_est = sigma / (kc * fc0d) if fc0d > 0 else float("inf")
    detalhe.update({"kc": kc, "estabilidade": "6.5.5",
                    "util_estabilidade": util_est,
                    "util": max(util_res, util_est),
                    "OK": bool(util_res <= 1.0 and util_est <= 1.0)})
    return detalhe


# Tab.8 (6.5.6): beta_M por h/b, para gamma_f = 1,4 e beta_E = 4.
TAB8_BETA_M = {1: 6.0, 2: 8.8, 3: 12.3, 4: 15.9, 5: 19.5, 6: 23.1,
               7: 26.7, 8: 30.3, 9: 34.0, 10: 37.6, 11: 41.2, 12: 44.8,
               13: 48.5, 14: 52.1, 15: 55.8, 16: 59.4, 17: 63.0,
               18: 66.7, 19: 70.3, 20: 74.0}


def beta_M(h_sobre_b):
    """beta_M da Tab.8 com interpolacao linear entre os h/b tabelados."""
    r = float(h_sobre_b)
    if not 1.0 - 1e-9 <= r <= 20.0 + 1e-9:
        raise EntradaMadeira(
            "h/b = %.2f fora da Tab.8 (1 a 20): secao fora do campo da "
            "dispensa de 6.5.6" % r)
    lo = int(min(max(math.floor(r), 1), 19))
    hi = lo + 1
    if abs(r - round(r)) < 1e-9:
        return TAB8_BETA_M[int(round(r))]
    v0, v1 = TAB8_BETA_M[lo], TAB8_BETA_M[hi]
    return v0 + (v1 - v0) * (r - lo)


def dispensa_estabilidade_lateral_656(b_m, h_m, L1_m, E0m, fmd, kmod_num,
                                      rotacao_apoio_impedida=True):
    """6.5.6: a viga retangular dispensa a verificacao de estabilidade
    lateral quando (a) as rotacoes nos apoios estao impedidas E (b)
    L1/b <= E0,ef/(beta_M . fm,d), com E0,ef = kmod1.kmod2.E0,med (5.8.7)
    e beta_M da Tab.8 pelo h/b.

    L1 e' a distancia entre pontos ADJACENTES da borda comprimida com
    deslocamento lateral impedido (apoios e travamentos). E' numero
    declarado, nao 'sim': era exatamente isso que a flag booleana deixava
    passar sem conferencia."""
    b, h, L1 = float(b_m), float(h_m), float(L1_m)
    if b <= 0 or h <= 0:
        raise EntradaMadeira("b e h devem ser > 0")
    if L1 < 0:
        raise EntradaMadeira("L1 (travamento da borda comprimida) deve "
                             "ser >= 0")
    if fmd <= 0:
        raise EntradaMadeira("fm,d deve ser > 0")
    bm = beta_M(h / b)
    E0ef = float(kmod_num) * float(E0m)
    limite = b * E0ef / (bm * fmd)
    ok_geo = L1 <= limite + 1e-12
    return {"criterio": "6.5.6_dispensa", "b_m": b, "h_m": h,
            "h_sobre_b": h / b, "beta_M": bm, "L1_m": L1,
            "E0ef_kNm2": E0ef, "L1_limite_m": limite,
            "rotacao_apoio_impedida": bool(rotacao_apoio_impedida),
            "dispensada": bool(ok_geo and rotacao_apoio_impedida),
            "motivo": (None if (ok_geo and rotacao_apoio_impedida)
                       else ("rotacao nos apoios nao impedida (6.5.6-a)"
                             if not rotacao_apoio_impedida
                             else "L1 = %.2f m acima de %.2f m = "
                                  "b.E0,ef/(beta_M.fm,d) (6.5.6-b)"
                                  % (L1, limite)))}


def verifica_flexao(Md_kNm, W_m3, fmd, estabilidade):
    """6.3.4: sigma = Md/W <= fm,d, mais a estabilidade lateral.

    `estabilidade`: saida de dispensa_estabilidade_lateral_656. So a
    dispensa CONFERIDA aprova; a verificacao por teoria experimental
    (6.5.6, quando a dispensa nao vale) segue fora do lote e a peca
    reprova nomeando o motivo."""
    if W_m3 <= 0:
        raise EntradaMadeira("modulo de resistencia W deve ser > 0")
    if not isinstance(estabilidade, dict) or "dispensada" not in estabilidade:
        raise EntradaMadeira(
            "estabilidade lateral deve vir de "
            "dispensa_estabilidade_lateral_656 (6.5.6): 'travado' como "
            "declaracao booleana nao e' conferencia")
    sigma = abs(float(Md_kNm)) / W_m3
    util = sigma / fmd if fmd > 0 else float("inf")
    ok_res = bool(util <= 1.0)
    disp = bool(estabilidade["dispensada"])
    return {"solicitacao": "flexao_reta_6.3.4", "sigma_kNm2": sigma,
            "resistencia_kNm2": fmd, "util": util,
            "estabilidade_lateral": estabilidade,
            "OK": bool(ok_res and disp),
            "motivo": (None if (ok_res and disp)
                       else (estabilidade["motivo"] if not disp
                             else "resistencia a flexao excedida"))}


# --- 9 disposicoes construtivas ---------------------------------------------
# 9.2.1: area e espessura minimas por papel da peca (cm2, cm).
MINIMOS_921 = {
    "principal_isolada": (50.0, 5.0),
    "secundaria_isolada": (18.0, 2.5),
    "principal_multipla": (35.0, 2.5),
    "secundaria_multipla": (18.0, 1.8),
}
RAZAO_L0_921 = {"comprimida": 40.0, "tracionada": 50.0}


def verifica_dimensoes_minimas_921(b_m, h_m, papel="principal_isolada"):
    """9.2.1: area minima da secao e espessura minima por papel da peca."""
    if papel not in MINIMOS_921:
        raise EntradaMadeira("papel %r invalido (9.2.1: %s)"
                             % (papel, ", ".join(MINIMOS_921)))
    A_cm2 = float(b_m) * float(h_m) * 1e4
    esp_cm = min(float(b_m), float(h_m)) * 100.0
    A_min, esp_min = MINIMOS_921[papel]
    falhas = []
    if A_cm2 < A_min - 1e-9:
        falhas.append("area %.1f < %.1f cm2" % (A_cm2, A_min))
    if esp_cm < esp_min - 1e-9:
        falhas.append("espessura %.1f < %.1f cm" % (esp_cm, esp_min))
    return {"criterio": "9.2.1", "papel": papel, "A_cm2": A_cm2,
            "espessura_cm": esp_cm, "A_min_cm2": A_min,
            "espessura_min_cm": esp_min, "falhas": falhas,
            "OK": not falhas}


def verifica_esbeltez_geometrica_93(L0_m, dim_m, solicitacao="comprimida"):
    """9.3: L0 nao pode passar de 40x a dimensao transversal
    correspondente na peca comprimida, nem de 50x na tracionada. E'
    limite GEOMETRICO proprio, ao lado do lambda <= 140 de 6.5.3."""
    if solicitacao not in RAZAO_L0_921:
        raise EntradaMadeira("solicitacao %r invalida (comprimida|"
                             "tracionada)" % (solicitacao,))
    if float(dim_m) <= 0:
        raise EntradaMadeira("dimensao transversal deve ser > 0")
    razao = float(L0_m) / float(dim_m)
    teto = RAZAO_L0_921[solicitacao]
    return {"criterio": "9.3", "solicitacao": solicitacao,
            "L0_sobre_dim": razao, "teto": teto,
            "OK": bool(razao <= teto + 1e-9),
            "motivo": (None if razao <= teto + 1e-9 else
                       "L0/dim = %.1f acima de %g (9.3)" % (razao, teto))}


def verifica_cisalhamento(Vd_kN, A_m2, fv0d):
    """6.4.2 retangular: tau = 1,5.V/A <= fv0,d."""
    if A_m2 <= 0:
        raise EntradaMadeira("area deve ser > 0")
    tau = 1.5 * abs(float(Vd_kN)) / A_m2
    util = tau / fv0d if fv0d > 0 else float("inf")
    return {"solicitacao": "cisalhamento_6.4.2", "tau_kNm2": tau,
            "resistencia_kNm2": fv0d, "util": util,
            "OK": bool(util <= 1.0)}


def verifica_flexocompressao(Nd_kN, Md_kNm, A_m2, W_m3, fc0d, fmd,
                             lam, fc0k, E005):
    """6.3.7 (quadratica na compressao, reta) + 6.5.5 (kc). Flexao reta."""
    if A_m2 <= 0 or W_m3 <= 0:
        raise EntradaMadeira("A e W devem ser > 0")
    sN = abs(float(Nd_kN)) / A_m2
    sM = abs(float(Md_kNm)) / W_m3
    util_res = (sN / fc0d) ** 2 + sM / fmd
    lam_rel = esbeltez_relativa(lam, fc0k, E005)
    if lam > LAMBDA_MAX:
        return {"solicitacao": "flexocompressao_6.3.7+6.5.5", "OK": False,
                "util_resistencia": util_res, "lambda": lam,
                "motivo": "lambda %.1f > 140 (6.5.3)" % lam}
    kc = 1.0 if lam_rel <= 0.3 else coef_flambagem(lam_rel)["kc"]
    util_est = sN / (kc * fc0d) + sM / fmd
    util = max(util_res, util_est)
    return {"solicitacao": "flexocompressao_6.3.7+6.5.5",
            "sigmaN_kNm2": sN, "sigmaM_kNm2": sM,
            "lambda": lam, "lambda_rel": lam_rel, "kc": kc,
            "util_resistencia": util_res, "util_estabilidade": util_est,
            "util": util, "OK": bool(util <= 1.0)}


DIST_EXTREMIDADE_ALFA1_CM = 7.5  # 6.2.4: abaixo disso, alfa_n = 1


def alfa_n(extensao_cm, dist_extremidade_cm=None):
    """alfa_n da Tab.6 (6.2.4) com interpolacao linear.

    A 6.2.4 tem DUAS condicoes que zeram o ganho, nao uma: "se a forca
    estiver aplicada a menos de 7,5 cm da extremidade da peca OU a' >= 15
    cm, admite-se alfa_n = 1". A extensao a' sozinha nao descreve a
    primeira - ela e' POSICAO, e quem chama e' que a conhece. Por isso
    `dist_extremidade_cm` e' explicito: None significa "posicao nao
    declarada" e, como o ganho da Tab.6 e' contra a seguranca quando a
    peca termina ali, None cai no PISO (alfa_n = 1). Quem tem apoio no
    meio da peca declara a distancia e recebe a tabela."""
    a = float(extensao_cm)
    if a <= 0:
        raise EntradaMadeira("extensao do carregamento deve ser > 0")
    if dist_extremidade_cm is None:
        return 1.00
    if float(dist_extremidade_cm) < DIST_EXTREMIDADE_ALFA1_CM:
        return 1.00
    if a >= 15.0:
        return 1.00
    if a <= 1.0:
        return _ALFA_N[0][1]
    for (a0, v0), (a1, v1) in zip(_ALFA_N, _ALFA_N[1:]):
        if a0 <= a <= a1:
            return v0 + (v1 - v0) * (a - a0) / (a1 - a0)
    return 1.00


def verifica_apoio(Rd_kN, A_apoio_m2, fc0d, extensao_cm,
                   dist_extremidade_cm=None):
    """Apoio com compressao perpendicular (6.3.3 + 6.2.4):
    fc90,d = 0,25.fc0,d.alfa_n; sigma <= fc90,d.

    `dist_extremidade_cm`: distancia da forca a extremidade da peca
    (6.2.4). Nao declarada = apoio na ponta = alfa_n 1 (ver alfa_n)."""
    if A_apoio_m2 <= 0:
        raise EntradaMadeira("area de apoio deve ser > 0")
    an = alfa_n(extensao_cm, dist_extremidade_cm)
    fc90d = 0.25 * fc0d * an
    sigma = abs(float(Rd_kN)) / A_apoio_m2
    util = sigma / fc90d if fc90d > 0 else float("inf")
    return {"solicitacao": "apoio_perpendicular_6.3.3+6.2.4",
            "sigma_kNm2": sigma, "fc90d_kNm2": fc90d, "alfa_n": an,
            "dist_extremidade_cm": dist_extremidade_cm,
            "util": util, "OK": bool(util <= 1.0)}


def hankinson(f0d, f90d, alpha_graus):
    """6.2.8: f_alpha (ignorar ate 6 graus)."""
    if abs(float(alpha_graus)) <= 6.0:
        return f0d
    a = math.radians(abs(float(alpha_graus)))
    return f0d * f90d / (f0d * math.sin(a) ** 2 + f90d * math.cos(a) ** 2)


def tracao_perpendicular_f90(ft0d):
    """6.2.3: ft90,d = 0,06.ft0,d (so para Hankinson, nunca sozinha)."""
    return 0.06 * ft0d


# --- embutimento e pino (6.2.5/7.1.3/7.1.4) ---------------------------------
def embutimento_fek(d_mm, rhok, conifera, com_prefuro=True, alpha_graus=0.0):
    """fe,k em N/mm2 (6.2.5). Pregos d < 8 mm tem equacao propria; d >= 8
    mm e parafusos ate 30 mm usam fe0,k com Hankinson (k90 por grupo)."""
    d = float(d_mm)
    if not 0 < d <= 30:
        raise EntradaMadeira("pino d deve estar em (0, 30] mm (6.2.5)")
    rho = float(rhok)
    if rho <= 0:
        raise EntradaMadeira("densidade caracteristica deve ser > 0")
    if d < 8:
        if com_prefuro:
            fek = 0.082 * (1.0 - 0.01 * d) * rho
        else:
            fek = 0.082 * rho * d ** (-0.3)
        return {"fe_k_Nmm2": fek, "fe0_k_Nmm2": fek, "k90": None,
                "equacao": "prego_d<8_" + ("com_prefuro" if com_prefuro
                                           else "sem_prefuro")}
    fe0 = 0.082 * (1.0 - 0.01 * d) * rho
    k90 = (1.35 + 0.015 * d) if conifera else (0.90 + 0.015 * d)
    a = math.radians(abs(float(alpha_graus)))
    fea = fe0 / (k90 * math.sin(a) ** 2 + math.cos(a) ** 2)
    return {"fe_k_Nmm2": fea, "fe0_k_Nmm2": fe0, "k90": k90,
            "equacao": "parafuso_Hankinson"}


def pino_Myk_Nmm(fuk_MPa, d_mm):
    """My,k = 0,3.fu.d^2,6 em N.mm (7.1.4)."""
    d = float(d_mm)
    if d <= 0 or float(fuk_MPa) <= 0:
        raise EntradaMadeira("fu,k e d do pino devem ser > 0")
    return 0.3 * float(fuk_MPa) * d ** 2.6


def n_efetivo(nc):
    """7.1.7: ate 8 soma tudo; acima, o excedente vale 2/3."""
    n = int(nc)
    if n < 2:
        raise EntradaMadeira("ligacao com menos de 2 pinos e' proibida "
                             "(7.1.1: nao sao permitidas com 1 pino)")
    if n <= 8:
        return float(n)
    return 8.0 + (2.0 / 3.0) * (n - 8)


# --- ligacao madeira-aco com pinos (7.3, modos a-l) --------------------------
# Rk por plano de corte e por pino, em N (fe em N/mm2, t/d em mm,
# My em N.mm). Efeito corda sem ensaio = 0 (conservador, dito).
def _rk_madeira_aco(config, fe1, fe2, t1, t2, d, My):
    fax = 0.0
    if config == "chapa_fina_simples":
        a = 0.4 * fe1 * t1 * d
        b = 1.15 * math.sqrt(2.0 * My * fe1 * d) + fax / 4.0
        return {"a_embutimento": a, "b_pino": b,
                "FvRk_N": min(a, b)}
    if config in ("chapa_grossa_simples", "chapa_central_dupla"):
        c = fe1 * t1 * d
        dd = (fe1 * t1 * d
              * (math.sqrt(2.0 + 4.0 * My / (fe1 * d * t1 ** 2)) - 1.0)
              + fax / 4.0)
        e = 2.3 * math.sqrt(My * fe1 * d) + fax / 4.0
        return {"c_embutimento": c, "d_misto": dd, "e_pino": e,
                "FvRk_N": min(c, dd, e)}
    if config == "chapas_laterais_finas_dupla":
        i = 0.5 * fe2 * t2 * d
        j = 1.15 * math.sqrt(2.0 * My * fe2 * d) + fax / 4.0
        return {"i_embutimento": i, "j_pino": j,
                "FvRk_N": min(i, j)}
    if config == "chapas_laterais_grossas_dupla":
        k = 0.5 * fe2 * t2 * d
        ll = 2.3 * math.sqrt(My * fe2 * d) + fax / 4.0
        return {"k_embutimento": k, "l_pino": ll,
                "FvRk_N": min(k, ll)}
    raise EntradaMadeira(
        "config %r invalida (7.3: chapa_fina_simples, chapa_grossa_simples,"
        " chapa_central_dupla, chapas_laterais_finas_dupla,"
        " chapas_laterais_grossas_dupla)" % (config,))


CONFIGS_73 = ("chapa_fina_simples", "chapa_grossa_simples",
              "chapa_central_dupla", "chapas_laterais_finas_dupla",
              "chapas_laterais_grossas_dupla")


def verifica_ligacao(Sd_kN, cfg):
    """No de tesoura em chapa de aco + pinos (7.1.2 + 7.3).

    cfg: {config_73, tipo_pino ('prego'|'parafuso'), d_mm, fu_MPa,
      t1_mm, t2_mm (madeira por plano), fe1_Nmm2, fe2_Nmm2 (de
      embutimento_fek), n_pinos, n_planos (nsp), kmod1, kmod2,
      espacamentos {a1,a2,a3t,a3c,a4t,a4c}_mm, alpha_graus,
      t_madeira_mm (menor espessura, p/ 7.2 a-f), penetracao_mm}.
    Rd = kmod1.kmod2.Rk/1,4 com kmod1 <= 1 no aco; Rk = nsp.nef.FvRk.
    Geometria minima (7.2 a-f, 7.1.9/7.1.10) vira gate: fura, reprova."""
    for chave in ("config_73", "tipo_pino", "d_mm", "fu_MPa", "t1_mm",
                  "fe1_Nmm2", "n_pinos", "n_planos", "kmod1", "kmod2"):
        if cfg.get(chave) is None:
            raise EntradaMadeira("ligacao precisa de '%s' declarado" % chave)
    config = cfg["config_73"]
    tipo = cfg["tipo_pino"]
    # 7.3: fina e' ts <= 0,5d; grossa e' ts >= d (com pre-furo <= 1,1d);
    # entre as duas a norma manda INTERPOLAR. A classe nao e' opiniao do
    # projetista: e' medida na chapa. Sem t_chapa_mm nao ha classificacao.
    if cfg.get("t_chapa_mm") is None:
        raise EntradaMadeira(
            "ligacao precisa de 't_chapa_mm': a chapa e' fina (ts <= 0,5d) "
            "ou grossa (ts >= d) pela ESPESSURA (7.3), nao pela declaracao")
    if tipo not in ("prego", "parafuso"):
        raise EntradaMadeira("tipo_pino %r fora do lote (prego|parafuso; "
                             "anel 7.4 e dente 7.5 fora do lote)" % (tipo,))
    d = float(cfg["d_mm"])
    fu = float(cfg["fu_MPa"])
    t1 = float(cfg["t1_mm"])
    t2 = float(cfg.get("t2_mm", t1))
    fe1 = float(cfg["fe1_Nmm2"])
    fe2 = float(cfg.get("fe2_Nmm2", fe1))
    nsp = int(cfg["n_planos"])
    if nsp < 1:
        raise EntradaMadeira("n_planos deve ser >= 1")
    # 7.1.9: diametros minimos.
    dmin = 3.0 if tipo == "prego" else 9.5
    gates_geo = []
    if d < dmin:
        gates_geo.append("d=%.2f < dmin=%.1f mm (7.1.9)" % (d, dmin))
    # 7.2 a-f: diametro x espessura e penetracao.
    t_menor = float(cfg.get("t_madeira_mm", min(t1, t2)))
    if tipo == "parafuso" and d > t_menor / 2.0:
        gates_geo.append("parafuso d=%.1f > t/2=%.1f mm (7.2-a)" % (d, t_menor / 2))
    if tipo == "prego" and d > t_menor / 5.0:
        gates_geo.append("prego d=%.1f > t/5=%.1f mm (7.2-b)" % (d, t_menor / 5))
    pen = cfg.get("penetracao_mm")
    if pen is not None:
        limite = 12.0 * d if tipo == "prego" else 6.0 * d
        if float(pen) < min(limite, t_menor):
            gates_geo.append("penetracao %.0f < min(%.0f, t) mm (7.2-%s)"
                             % (float(pen), limite,
                                "d" if tipo == "prego" else "f"))
    # 7.1.10: espacamentos minimos (Tab.14, alpha declarado).
    esp = cfg.get("espacamentos") or {}
    alpha = float(cfg.get("alpha_graus", 0.0))
    req = espacamentos_minimos(tipo, d, alpha, com_prefuro=True)
    for chave in ("a1", "a2", "a3t", "a3c", "a4t", "a4c"):
        if esp.get(chave) is not None and float(esp[chave]) < req[chave] - 1e-9:
            gates_geo.append("%s=%.0f < %.0f mm (Tab.14, alpha=%.0f)"
                             % (chave, float(esp[chave]), req[chave], alpha))
    ts = float(cfg["t_chapa_mm"])
    if ts <= 0:
        raise EntradaMadeira("t_chapa_mm deve ser > 0")
    classe_chapa = ("fina" if ts <= 0.5 * d + 1e-9
                    else ("grossa" if ts >= d - 1e-9 else "intermediaria"))
    declarada = "fina" if "fina" in config else (
        "grossa" if "grossa" in config else "qualquer")
    # a chapa central de dupla secao vale "de qualquer espessura" (7.3).
    if config != "chapa_central_dupla":
        if classe_chapa == "intermediaria":
            gates_geo.append(
                "chapa ts=%.1f mm entre 0,5d=%.1f e d=%.1f: a 7.3 manda "
                "INTERPOLAR entre fina e grossa (fora do lote); declare "
                "uma chapa que caia numa das duas classes"
                % (ts, 0.5 * d, d))
        elif classe_chapa != declarada:
            gates_geo.append(
                "chapa ts=%.1f mm e' %s (7.3), mas config_73 declara %s: "
                "os modos de falha sao outros" % (ts, classe_chapa,
                                                  declarada))
    My = pino_Myk_Nmm(fu, d)
    modos = _rk_madeira_aco(config, fe1, fe2, t1, t2, d, My)
    FvRk_N = modos["FvRk_N"]
    nef = n_efetivo(cfg["n_pinos"])
    Rk_N = nsp * nef * FvRk_N
    k1 = min(float(cfg["kmod1"]), 1.0)  # 7.1.2: teto no aco
    Rd_N = k1 * float(cfg["kmod2"]) * Rk_N / GAMMA_LIG
    Sd_N = abs(float(Sd_kN)) * 1000.0
    util = Sd_N / Rd_N if Rd_N > 0 else float("inf")
    ok = bool(util <= 1.0 and not gates_geo)
    return {"solicitacao": "ligacao_madeira_aco_7.3_%s" % config,
            "tipo_pino": tipo, "d_mm": d, "My_Nmm": My,
            "FvRk_por_plano_N": FvRk_N, "n_planos": nsp,
            "n_pinos": int(cfg["n_pinos"]), "nef": nef,
            "Rk_N": Rk_N, "Rd_kN": Rd_N / 1000.0,
            "kmod1_usado": k1, "kmod2_usado": float(cfg["kmod2"]),
            "modos_N": {k: v for k, v in modos.items() if k != "FvRk_N"},
            "governa": min((k for k in modos if k != "FvRk_N"),
                           key=lambda k: modos[k]),
            "t_chapa_mm": ts, "classe_chapa_73": classe_chapa,
            "geometria": req, "falhas_geometria": gates_geo,
            "efeito_corda": "FaxRk=0 sem ensaio (conservador)",
            "util": util, "OK": ok}


def espacamentos_minimos(tipo, d_mm, alpha_graus=0.0, com_prefuro=True):
    """Minimos da Tab.14 (7.1.10) em mm para o alpha declarado.

    Pregos valem com pre-furacao (7.1.11); sem ela a ligacao e'
    provisoria e sai do lote. Leitura da p.65-66 do PDF (F136)."""
    if tipo not in ("prego", "parafuso"):
        raise EntradaMadeira("espacamentos so para prego|parafuso")
    d = float(d_mm)
    a = math.radians(abs(float(alpha_graus)))
    ca, sa = abs(math.cos(a)), abs(math.sin(a))
    if tipo == "prego":
        if not com_prefuro:
            raise EntradaMadeira("prego sem pre-furacao e' provisoria "
                                 "(7.1.11): fora do lote")
        a1 = (4.0 + 3.0 * ca) * d
        a2 = (3.0 + 6.0 * sa) * d  # Tab.14, linha a2 de prego com pre-furo.
        a3t = (7.0 + 5.0 * ca) * d
        a3c = 7.0 * d
        a4t = (3.0 + (2.0 if d < 5 else 4.0) * sa) * d
        a4c = 3.0 * d
    else:
        a1 = (4.0 + 3.0 * ca) * d
        a2 = 4.0 * d
        a3t = max(7.0 * d, 80.0)
        a3c = 4.0 * d
        a4t = max((2.0 + 2.0 * sa) * d, 3.0 * d)
        a4c = 3.0 * d
    return {"a1": a1, "a2": a2, "a3t": a3t, "a3c": a3c, "a4t": a4t,
            "a4c": a4c, "alpha_graus": alpha_graus}


def verifica_tracao_perp_no(Fvd_kN, b_mm, h_mm, he_mm, kmod_num):
    """7.1.1: Fv,Ed <= F90,Rd no no com forca inclinada.
    F90,Rk = 14.b.sqrt(he/(1-he/h)) em N (b/h/he em mm)."""
    b, h, he = float(b_mm), float(h_mm), float(he_mm)
    if not 0 < he < h:
        raise EntradaMadeira("he deve estar em (0, h) para F90")
    F90Rk_N = 14.0 * b * math.sqrt(he / (1.0 - he / h))
    F90Rd_kN = float(kmod_num) * F90Rk_N / GAMMA_LIG / 1000.0
    util = abs(float(Fvd_kN)) / F90Rd_kN if F90Rd_kN > 0 else float("inf")
    return {"solicitacao": "tracao_perp_no_7.1.1", "F90Rk_N": F90Rk_N,
            "F90Rd_kN": F90Rd_kN, "util": util,
            "OK": bool(util <= 1.0)}


# --- ELS: flecha de viga biapoiada (8) --------------------------------------
def flecha_biapoiada(w_kN_m, L_m, E_kNm2, I_m4):
    """delta_inst = 5.w.L^4/(384.E.I) em m (comportamento elastico, 8.1)."""
    return 5.0 * float(w_kN_m) * L_m ** 4 / (384.0 * E_kNm2 * I_m4)


# Tab.21 (8.2), viga biapoiada ou continua: a norma da FAIXA, nao numero.
# Sem limite declarado vale o extremo ESTRITO de cada faixa (regra do piso
# conservador para dado ausente); declarado, tem de cair DENTRO da faixa.
TAB21_BIAPOIADA = {
    "inst": (300.0, 500.0),      # L/300 a L/500
    "fin": (150.0, 300.0),       # L/150 a L/300
    "net_fin": (250.0, 350.0),   # L/250 a L/350
}


def limites_tab21(declarados=None, tipo="biapoiada"):
    """Denominadores de Tab.21 por deslocamento, com a faixa como guarda.

    `declarados`: {"inst": 400, ...} - denominador de L/n. Fora da faixa
    da Tab.21 RECUSA com o intervalo (nao satura no limite: D82)."""
    if tipo != "biapoiada":
        raise EntradaMadeira(
            "Tab.21 aqui so cobre viga biapoiada ou continua; balanco "
            "(L/150-250, L/75-150, L/125-175) fora do lote")
    esc = {}
    dec = declarados or {}
    for chave, (folgado, estrito) in TAB21_BIAPOIADA.items():
        if dec.get(chave) is None:
            esc[chave] = estrito
            continue
        n = float(dec[chave])
        if not folgado - 1e-9 <= n <= estrito + 1e-9:
            raise EntradaMadeira(
                "limite %s = L/%g fora da faixa da Tab.21 (L/%g a L/%g)"
                % (chave, n, folgado, estrito))
        esc[chave] = n
    return esc


def verifica_els_terca(wG_kN_m, wQ_kN_m, L_m, E0m, I_m4, classe_umidade,
                       forro_fragil=False, contraflecha_m=0.0,
                       limites=None):
    """8.1 + Tab.20/21: flecha instantanea, final e final liquida.

    delta_fin com a fluencia phi da Tab.20 (psi2 = 1: conservador, dito).
    delta_net,fin desconta a contraflecha (8.2 limita a contraflecha a 2/3
    da flecha permanente instantanea; acima disso RECUSA). Os limites saem
    de limites_tab21: sem declaracao, o extremo estrito da faixa - nunca
    um numero do meio dela, que a Tab.21 nao traz. Com forro fragil, a
    flecha da VARIAVEL tambem respeita L/500 e 15 mm (8.2)."""
    phi = FLUENCIA_SERRADA[int(classe_umidade)]
    dG = flecha_biapoiada(wG_kN_m, L_m, E0m, I_m4)
    dQ = flecha_biapoiada(wQ_kN_m, L_m, E0m, I_m4)
    dinst = dG + dQ
    dfin = dG * (1.0 + phi) + dQ * (1.0 + phi)
    cf = float(contraflecha_m or 0.0)
    if cf < 0:
        raise EntradaMadeira("contraflecha nao pode ser negativa")
    if cf > (2.0 / 3.0) * dG + 1e-12:
        raise EntradaMadeira(
            "contraflecha %.1f mm acima de 2/3 da flecha permanente "
            "instantanea (%.1f mm), teto da 8.2"
            % (cf * 1000.0, (2.0 / 3.0) * dG * 1000.0))
    dnet = dfin - cf
    lim = limites_tab21(limites)
    lim_inst = L_m / lim["inst"]
    lim_fin = L_m / lim["fin"]
    lim_net = L_m / lim["net_fin"]
    excedidos = []
    if dinst > lim_inst:
        excedidos.append("inst (L/%g)" % lim["inst"])
    if dfin > lim_fin:
        excedidos.append("fin (L/%g)" % lim["fin"])
    if dnet > lim_net:
        excedidos.append("net_fin (L/%g)" % lim["net_fin"])
    ok = not excedidos
    motivo = None
    if forro_fragil:
        ok_var = dQ <= min(L_m / 500.0, 0.015)
        if not ok_var:
            ok = False
            motivo = "flecha variavel excede L/500 ou 15 mm (forro fragil)"
    if motivo is None and excedidos:
        motivo = "flecha excede a Tab.21 em: " + ", ".join(excedidos)
    return {"solicitacao": "els_flecha_8", "d_inst_m": dinst,
            "d_fin_m": dfin, "d_net_fin_m": dnet,
            "contraflecha_m": cf,
            "lim_inst_m": lim_inst, "lim_fin_m": lim_fin,
            "lim_net_fin_m": lim_net, "limites_L_sobre": lim,
            "phi": phi, "psi2": "1 (conservador)",
            "OK": bool(ok), "motivo": motivo}


def escopo():
    """O que este modulo cobre e o que deixa de fora, dito em voz alta."""
    return {
        "classes_tab3": "implemented",
        "kmod_tab4_tab5": "implemented",
        "tracao_6.3.2": "implemented",
        "compressao_estabilidade_6.3.3_6.5": "implemented",
        "flexao_reta_6.3.4": "implemented",
        "estabilidade_lateral_6.5.6": "dispensa_implementada",
        "cisalhamento_6.4.2": "implemented",
        "flexocompressao_6.3.7_6.5.5": "implemented",
        "apoio_perpendicular_6.3.3_6.2.4": "implemented",
        "embutimento_6.2.5": "implemented",
        "pino_7.1.4_grupo_7.1.7": "implemented",
        "ligacao_madeira_aco_7.3": "implemented",
        "ligacao_madeira_madeira_7.2": "not_available",
        "aneis_7.4": "not_available",
        "chapas_dentes_7.5": "not_available",
        "els_flecha_8": "implemented",
        "dimensoes_minimas_9.2.1": "implemented",
        "esbeltez_geometrica_9.3": "implemented",
        "cortante_reduzida_apoio_6.4.3": "not_available",
        "flexao_obliqua_6.3.5_flexotracao_6.3.6": "not_available",
        "MLC_MLCC_LVL_CLT": "not_available",
        "vento_succao_uplift": "not_available",
    }


def motivos_escopo():
    """Motivo e endereco de cada fora do lote."""
    return {
        "estabilidade_lateral_6.5.6":
            "a DISPENSA da 6.5.6 esta implementada (Tab.8: rotacao nos "
            "apoios impedida e L1 <= b.E0,ef/(beta_M.fm,d)); fora da "
            "dispensa, a verificacao por teoria comprovada "
            "experimentalmente segue fora do lote e a peca reprova",
        "cortante_reduzida_apoio_6.4.3":
            "a reducao de Vd a 0 <= z <= 2h (6.4.3) e' permissao, nao "
            "exigencia: nao aplica-la e' conservador e evita depender da "
            "posicao declarada da carga",
        "flexao_obliqua_6.3.5_flexotracao_6.3.6":
            "a tesoura do G66 tem carga so nos nos (esforco axial) e "
            "terca em flexao reta; obliqua e flexotracao entram quando "
            "houver telhado com carga fora do plano da terca",
        "ligacao_madeira_madeira_7.2":
            "Tab.17/18 sem transcricao inequivoca no lote: o no sai em "
            "chapa de aco (7.3, modos a-l legiveis)",
        "aneis_7.4": "resistencia pelo ensaio da NBR 7190-5 (7.4): sem "
                     "ensaio nao ha numero",
        "chapas_dentes_7.5": "resistencia assegurada pelo fabricante "
                             "(7.5): sem catalogo nao ha numero",
        "MLC_MLCC_LVL_CLT": "G66 e' madeira serrada/rolica; lamelada, "
                            "cruzada, laminada e CLT sao outro lote",
        "vento_succao_uplift": "cadeia gravitacional como a da casa: "
                               "vento e succao no telhado fora do lote",
    }


def relatorio_pt(r):
    """Linha-resumo das resistencias de calculo e do kmod."""
    L = ["MADEIRA SERRADA (NBR 7190-1 %s)" % FONTE,
         "  classe %s (%s) ; kmod = %.3f x %.3f = %.4f ; gamma_w = %.1f" % (
             r["classe"], "conifera" if r["conifera"] else "folhosa",
             r["kmod1"], r["kmod2"], r["kmod"], r["gamma_w"]),
         "  ft0,d = %.0f ; fc0,d = %.0f ; fm,d = %.0f ; fv0,d = %.0f kN/m2"
         % (r["ft0d"], r["fc0d"], r["fmd"], r["fv0d"])]
    return "\n".join(L)


def _selftest():
    # Tab.3 pontual: C24 e D40 transcritos da p.12.
    p = propriedades_classe("C24")
    assert (p["fbk_MPa"], p["ft0k_MPa"], p["fc0k_MPa"],
            p["fvk_MPa"]) == (24, 14, 21, 4.0), p
    assert (p["E0m_GPa"], p["E005_GPa"], p["rhok"]) == (11, 7.4, 350), p
    assert p["conifera"] is True
    d = propriedades_classe("d40")
    assert (d["fbk_MPa"], d["fc90k_MPa"], d["fvk_MPa"]) == (40, 8.3, 4.0), d
    assert d["conifera"] is False
    # sem default: vazio recusa; Tab.2 recusa com endereco.
    for ruim in (None, "", "C99"):
        try:
            propriedades_classe(ruim)
        except EntradaMadeira:
            pass
        else:
            raise AssertionError(ruim)
    try:
        propriedades_classe("D20")
    except EntradaMadeira as exc:
        assert "7190-3" in str(exc), exc
    else:
        raise AssertionError("D20")
    # kmod: longa x umidade 2 serrada = 0,70 x 0,90.
    k = kmod("longa", 2, "serrada")
    assert k["kmod"] == 0.63, k
    assert kmod("media", 1, "recomposta")["kmod"] == 0.65
    try:
        kmod("longa", 2, "MLC")
    except EntradaMadeira:
        pass
    else:
        raise AssertionError("MLC")
    # fd = kmod.fk/gamma: C24 curta/u1 serrada (0,90) -> fm,d = 15,43 MPa.
    r = resistencias_calculo(propriedades_classe("C24"), 0.90)
    assert abs(r["fmd"] - 0.90 * 24000 / 1.4) < 1e-6, r
    assert abs(r["fv0d"] - 0.90 * 4000 / 1.8) < 1e-6, r
    # tracao: 20 kN em 0,005 m2 com ft0,d = 9000 -> util 0,444.
    t = verifica_tracao(20.0, 0.005, 9000.0)
    assert abs(t["util"] - 20 / 0.005 / 9000) < 1e-9 and t["OK"], t
    # cisalhamento retangular: 1,5.V/A.
    c = verifica_cisalhamento(6.0, 0.012, 2000.0)
    assert abs(c["tau_kNm2"] - 750.0) < 1e-9 and c["OK"], c
    # My,k: d=12 fu=415 -> 0,3.415.12^2,6.
    assert abs(pino_Myk_Nmm(415.0, 12.0)
               - 0.3 * 415.0 * 12.0 ** 2.6) < 1e-6
    assert n_efetivo(6) == 6.0 and n_efetivo(11) == 10.0
    try:
        n_efetivo(1)
    except EntradaMadeira:
        pass
    else:
        raise AssertionError("1 pino")
    return True


if __name__ == "__main__":
    _selftest()
    print("madeira_nbr7190: selftest OK")
