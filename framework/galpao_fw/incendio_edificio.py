# ============================================================================
# incendio_edificio.py - SAIDAS DE EMERGENCIA DO EDIFICIO MULTIPAVIMENTO
#
# O adaptador do edificio declarava DISCIPLINES = ("estrutura",): o predio saia
# calculado, desenhado e modelado, e legalmente INOCUPAVEL - nada dimensionava
# a rota de abandono. Este modulo e' a fronteira entre o resultado da estrutura
# e os modulos de incendio que ja existiam aferidos, no mesmo formato do G9:
#
#     pavimentos + atividade declarada
#          -> populacao_nbr9077.populacao        (Tab.4, por pavimento)
#          -> perfil de risco de vida            (Tab.1 x Tab.2 -> Tab.3)
#          -> numero de rotas (Tab.5) / distancia a percorrer (Tab.6 + Tab.7)
#          -> largura das rotas HORIZONTAIS (Tab.8)
#          -> largura das rotas VERTICAIS  (Tab.10) e tipo de escada (Tab.11)
#          -> iluminacao_emergencia_nbr10898 / sinalizacao_nbr16820 /
#             deteccao_alarme_nbr17240 / hidrantes_nbr13714      (13.1-13.3)
#          -> gates
#
# A ESCADA E' UMA SO. Este e' o ponto em que o projeto pode se partir em dois: a
# estrutura dimensiona uma escada de concreto (escada_concreto, via
# estrutura.escada) e a 9077 exige uma largura minima. Se o vertical de incendio
# dimensionasse a SUA escada, o predio teria duas - o mesmo defeito que o G8
# achou na ancoragem viga-pilar, em que cada emissor tinha a sua. Aqui a largura
# e' UMA DECLARACAO (estrutura.escada.largura), que a estrutura usa e que este
# modulo LE e VERIFICA. Escada nao declarada nao vira escada arbitrada: vira
# erro nomeado. A largura calculada NUNCA e' adotada por conta propria; ela
# entra no gate como exigencia contra o valor declarado.
#
# ASK, DO NOT INVENT. Tres dados sao CLASSIFICACAO de responsavel tecnico e nao
# saem do modelo:
#   - a atividade de cada pavimento (Tab.4), que fixa a densidade;
#   - a classe do ocupante (Tab.1) - derivavel da atividade pelos EXEMPLOS da
#     propria Tab.1 quando ha correspondencia literal, e so entao;
#   - a velocidade de desenvolvimento do incendio (Tab.2), que depende da carga
#     de incendio e dos materiais - NAO ha default; sem ela nao ha perfil de
#     risco, e sem perfil de risco nao ha largura nem distancia.
#
# O QUE NAO ENTRA (publicado no escopo, nunca calado):
#   - o LEIAUTE: as distancias a percorrer e a largura dos corredores sao
#     medidas na planta de arquitetura, que este framework nao tem para o
#     edificio. Elas sao DECLARADAS e verificadas; nao medidas;
#   - antecamara, pressurizacao e dutos de ventilacao da escada a prova de
#     fumaca (NBR 14880): o modulo diz QUAL tipo a Tab.11 exige, e nao
#     dimensiona a ventilacao;
#   - compartimentacao e TRRF (NBR 14432/15200/16945): outro vertical;
#   - abandono faseado (9.4.4) e horizontal progressivo (7.5.7): dependem de
#     plano de gestao e brigada (Anexo A), decisao que nao e' de calculo.
#
# Unidades: m, m2, pessoas. STATELESS.
# CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL.
# ============================================================================
"""Saidas de emergencia do edificio multipavimento (ABNT NBR 9077:2025):
populacao, rotas, distancias, larguras e tipo de escada, com a largura da
escada lida da UNICA declaracao que a estrutura tambem usa."""

from __future__ import annotations

import math

import populacao_nbr9077 as pop

# --- NBR 9050:2020, o piso geometrico da escada -----------------------------
# 6.8.3: "A largura das escadas deve ser estabelecida de acordo com o fluxo de
# pessoas, conforme a ABNT NBR 9077. A largura minima para escadas em rotas
# acessiveis e' de 1,20 m". A 9077 9.4.2.2 devolve a bola: a largura minima
# atende a 9050, exceto quando a calculada for maior.
ESCADA_LARGURA_MIN_M = 1.20
PATAMAR_MIN_M = 1.20                 # 6.8.8 (dimensao longitudinal minima)
DESNIVEL_MAX_SEM_PATAMAR_M = 3.20    # 6.8.7 (um patamar a cada 3,20 m)
BLONDEL_9050_M = (0.63, 0.65)        # 6.8.2 a) 0,63 <= p + 2e <= 0,65
PISO_9050_M = (0.28, 0.32)           # 6.8.2 b)
ESPELHO_9050_M = (0.16, 0.18)        # 6.8.2 c)
# 6.11.1: larguras minimas de corredor por extensao (uso comum) e uso publico.
CORREDOR_MIN_M = ((4.0, 0.90), (10.0, 1.20), (math.inf, 1.50))
CORREDOR_USO_PUBLICO_MIN_M = 1.50

# --- NBR 9077:2025 Tabela 1 - caracteristicas dos ocupantes -----------------
OCUPANTES = {
    "A": "Familiarizados e despertos (em estado de vigilia)",
    "B": "Despertos e nao familiarizados",
    "Ci": "Podem estar adormecidos; familiarizados e em atividade de longa duracao",
    "Cii": "Podem estar adormecidos; familiarizados, atividade de longa duracao "
           "(superior a 30 dias) com gestao",
    "Ciii": "Podem estar adormecidos; nao familiarizados, atividade de curta "
            "duracao com gestao",
    "D": "Que recebem cuidados medicos ou especiais",
    "E": "Em transito",
}

# Derivacao da classe do ocupante a partir da atividade, pelos EXEMPLOS da
# propria Tabela 1 ("Edificios residenciais multifamiliar em geral" -> Ci,
# "Escritorios nao abertos ao publico" -> A, "Hoteis, Apart-hoteis" -> Ciii...).
# So ha entrada onde a Tab.1 nomeia a atividade; o resto exige declaracao.
OCUPANTE_POR_ATIVIDADE = {
    "habitacao_unifamiliar": "Ci",
    "habitacao_multifamiliar": "Ci",
    "habitacao_coletiva": "Cii",
    "hotel": "Ciii",
    "hotel_residencial": "Ciii",
    "servico_profissional": "A",
    "industria_geral": "A",
    "escola_geral": "A",
    "deposito_geral": "A",
    "centro_de_compras": "B",
    "comercio_geral": "B",
    "agencia_bancaria": "B",
    "pre_escola": "D",
    "escola_deficientes": "D",
}

# --- Tabela 2 - velocidade de crescimento do incendio -----------------------
VELOCIDADES = {
    1: {"nome": "lenta", "T_s": 600,
        "criterio": "carga de incendio especifica qf <= 300 MJ/m2 ou materiais "
                    "de contribuicao insignificante"},
    2: {"nome": "moderada", "T_s": 300,
        "criterio": "materiais de contribuicao moderada; nao se enquadrando nas "
                    "demais velocidades"},
    3: {"nome": "rapida", "T_s": 150,
        "criterio": "plasticos/texteis sinteticos empilhados, 3,0 m < H <= 5,0 m, "
                    "risco extraordinario grupo 1 (NBR 10897)"},
    4: {"nome": "ultrarrapida", "T_s": 75,
        "criterio": "empilhamento h > 5,0 m, risco extraordinario grupo 2, "
                    "liquidos/gases combustiveis, plasticos celulares"},
}

# --- Tabela 3 - perfil de risco de vida -------------------------------------
# Nota da Tab.3: "Para os perfis de risco B, C, D e E nao pode ser aceito o
# crescimento do fogo ultrarrapido (4), e nao pode se aceitar o crescimento
# rapido (3) para o perfil D".
_FAMILIA = {"A": "A", "B": "B", "Ci": "C", "Cii": "C", "Ciii": "C",
            "D": "D", "E": "E"}
VELOCIDADE_MAX_POR_FAMILIA = {"A": 4, "B": 3, "C": 3, "D": 2, "E": 3}


def perfil_risco(ocupante, velocidade):
    """Perfil de risco de vida (Tab.3) a partir da Tab.1 x Tab.2."""
    if ocupante not in OCUPANTES:
        raise ValueError("ocupante %r nao consta da Tabela 1 (use uma de: %s)"
                         % (ocupante, ", ".join(OCUPANTES)))
    if velocidade not in VELOCIDADES:
        raise ValueError("velocidade_incendio %r nao consta da Tabela 2 "
                         "(use 1, 2, 3 ou 4)" % (velocidade,))
    familia = _FAMILIA[ocupante]
    maxima = VELOCIDADE_MAX_POR_FAMILIA[familia]
    if velocidade > maxima:
        raise ValueError(
            "a Tabela 3 NAO admite a combinacao ocupante %s (familia %s) com "
            "velocidade de crescimento %d (%s): a velocidade maxima aceita para "
            "essa familia e' %d. Medidas adicionais de protecao (supressao) "
            "podem baixar uma categoria de risco (7.5.5.4), e essa decisao e' "
            "de projeto, nao deste modulo"
            % (ocupante, familia, velocidade, VELOCIDADES[velocidade]["nome"],
               maxima))
    return "%s%d" % (familia, velocidade)


# --- Tabela 5 - numero minimo de rotas de saida -----------------------------
# (populacao maxima, numero minimo de rotas)
ROTAS_MINIMAS = ((100, 1), (500, 2), (1000, 3))
ROTAS_ACIMA_DE_MIL = 4


def rotas_minimas(populacao_pav):
    """Numero minimo de rotas de saida de um pavimento (Tab.5)."""
    for maximo, n in ROTAS_MINIMAS:
        if populacao_pav <= maximo:
            return n
    return ROTAS_ACIMA_DE_MIL


# --- Tabela 6 - distancias maximas a serem percorridas (m) ------------------
# {perfil: (rotas alternativas, rota em uma unica direcao)}
DISTANCIA_MAX_M = {
    "A1": (70, 30), "A2": (60, 25), "A3": (45, 20), "A4": (30, 15),
    "B1": (60, 25), "B2": (50, 20), "B3": (40, 15),
    "C1": (45, 30), "C2": (35, 20), "C3": (25, 15),
    "D1": (30, 15), "D2": (20, 10),
    "E1": (60, 25), "E2": (50, 20), "E3": (40, 15),
}

# --- Tabela 7 - ganhos de caminhamento --------------------------------------
GANHO_DETECCAO_PCT = 15.0
GANHO_CONTROLE_FUMACA_PCT = 20.0
# (altura maxima do local que serve de via de escape, ganho %)
GANHO_ALTURA_PCT = ((3.0, 0.0), (4.0, 5.0), (5.0, 10.0), (6.0, 15.0),
                    (7.0, 18.0), (8.0, 21.0), (9.0, 24.0), (10.0, 27.0),
                    (math.inf, 30.0))
GANHO_MAX_PCT = 36.0                 # 7.5.5.2 (efeito acumulativo)
UNICA_DIRECAO_TETO_M = 30.0          # 7.5.5.2
REDUCAO_SEM_LEIAUTE_PCT = 30.0       # 7.5.4.1


def ganho_altura_pct(pe_direito_rota_m):
    """Ganho de caminhamento pela altura do local de escape (Tab.7)."""
    for limite, ganho in GANHO_ALTURA_PCT:
        if pe_direito_rota_m <= limite + 1e-9:
            return ganho
    return GANHO_ALTURA_PCT[-1][1]


def distancia_maxima(perfil, *, pe_direito_rota_m=None, deteccao=False,
                     controle_fumaca=False, leiaute_definido=True):
    """Distancias maximas a percorrer (Tab.6), com os ganhos da Tab.7.

    7.5.5.2: o efeito acumulativo dos ganhos nao pode ultrapassar 36 %, e o
    caminhamento em uma so direcao nao pode ultrapassar 30 m. 7.5.4.1: rota nao
    definida no projeto de arquitetura sofre REDUCAO de 30 %.
    """
    if perfil not in DISTANCIA_MAX_M:
        raise ValueError("perfil de risco %r sem linha na Tabela 6" % (perfil,))
    base_alt, base_uni = DISTANCIA_MAX_M[perfil]
    ganho = 0.0
    parcelas = []
    if deteccao:
        ganho += GANHO_DETECCAO_PCT
        parcelas.append(("deteccao_e_alarme", GANHO_DETECCAO_PCT))
    if controle_fumaca:
        ganho += GANHO_CONTROLE_FUMACA_PCT
        parcelas.append(("controle_de_fumaca_e_calor", GANHO_CONTROLE_FUMACA_PCT))
    if pe_direito_rota_m is not None:
        g = ganho_altura_pct(float(pe_direito_rota_m))
        if g:
            ganho += g
            parcelas.append(("altura_do_local", g))
    ganho_bruto = ganho
    ganho = min(ganho, GANHO_MAX_PCT)
    fator = 1.0 + ganho / 100.0
    if not leiaute_definido:
        fator *= 1.0 - REDUCAO_SEM_LEIAUTE_PCT / 100.0
    alternativas = base_alt * fator
    unica = min(base_uni * fator, UNICA_DIRECAO_TETO_M)
    return {
        "perfil": perfil,
        "base_alternativas_m": float(base_alt), "base_unica_m": float(base_uni),
        "ganho_pct": ganho, "ganho_bruto_pct": ganho_bruto,
        "ganho_saturou": ganho_bruto > GANHO_MAX_PCT + 1e-9,
        "parcelas_ganho": parcelas,
        "reducao_sem_leiaute": not leiaute_definido,
        "alternativas_m": round(alternativas, 2),
        "unica_direcao_m": round(unica, 2),
        "unica_direcao_teto_aplicado": base_uni * fator > UNICA_DIRECAO_TETO_M + 1e-9,
    }


# --- Tabela 8 - largura por pessoa nas rotas HORIZONTAIS (mm/pessoa) --------
LARGURA_PESSOA_HORIZ_MM = {
    "A1": 3.4, "A2": 3.8, "A3": 4.6, "A4": 12.3,
    "B1": 3.6, "B2": 4.1, "B3": 6.2,
    "C1": 3.6, "C2": 4.1, "C3": 6.2,
    "D1": 4.1, "D2": 6.2,
    "E1": 3.6, "E2": 4.1, "E3": 6.2,
}

# --- Tabela 10 - largura por pessoa nas saidas VERTICAIS (mm/pessoa) --------
# Colunas: 1o ao 10o andar ou superior. A linha e' o perfil de risco; as linhas
# da norma agrupam perfis ("B1, C1, E1"), aqui expandidas uma a uma.
_LARGURA_VERT_LINHAS = {
    ("A1",): (4.00, 3.60, 3.25, 3.00, 2.75, 2.55, 2.40, 2.25, 2.10, 2.00),
    ("B1", "C1", "E1"): (4.25, 3.80, 3.40, 3.10, 2.85, 2.65, 2.45, 2.30, 2.15, 2.05),
    ("A2",): (4.55, 4.00, 3.60, 3.25, 3.00, 2.75, 2.55, 2.40, 2.25, 2.10),
    ("B2", "C2", "D1", "E2"): (4.90, 4.30, 3.80, 3.45, 3.15, 2.90, 2.65, 2.50,
                               2.30, 2.15),
    ("A3",): (5.50, 4.75, 4.20, 3.75, 3.35, 3.10, 2.85, 2.60, 2.45, 2.30),
    ("B3", "C3", "D2", "E3"): (7.30, 6.40, 5.70, 5.15, 4.70, 4.30, 4.00, 3.70,
                               3.45, 3.25),
    ("A4",): (14.60, 11.40, 9.35, 7.95, 6.90, 6.10, 5.45, 4.95, 4.50, 4.15),
}
LARGURA_PESSOA_VERT_MM = {perfil: valores
                          for perfis, valores in _LARGURA_VERT_LINHAS.items()
                          for perfil in perfis}
# nota (F) da Tab.10: a coluna do 2o andar e' a do abandono FASEADO.
COLUNA_ABANDONO_FASEADO = 2


def largura_pessoa_vertical_mm(perfil, andar_mais_elevado):
    """Largura por pessoa (Tab.10) do piso mais elevado ocupado (9.4.3)."""
    if perfil not in LARGURA_PESSOA_VERT_MM:
        raise ValueError("perfil de risco %r sem linha na Tabela 10 (perfis B4 "
                         "e C4 nao sao aceitaveis pela Norma)" % (perfil,))
    if andar_mais_elevado < 1:
        raise ValueError("andar mais elevado ocupado deve ser >= 1")
    coluna = min(int(andar_mais_elevado), 10) - 1
    return LARGURA_PESSOA_VERT_MM[perfil][coluna]


# --- Tabela 11 - tipo de escada por ocupante x altura da edificacao ---------
# Cada faixa: (altura maxima em m, tipo). math.inf fecha a ultima.
TIPOS_ESCADA = ("aberta", "protegida", "antecamara_ventilada", "pressurizada")
TIPO_ESCADA_TAB11 = {
    "A":    ((6.0, "aberta"), (30.0, "protegida"), (math.inf, "prova_de_fumaca")),
    "B":    ((6.0, "aberta"), (12.0, "protegida"), (math.inf, "prova_de_fumaca")),
    "Ci":   ((12.0, "aberta"), (30.0, "protegida"), (math.inf, "prova_de_fumaca")),
    "Cii":  ((6.0, "aberta"), (30.0, "protegida"), (math.inf, "prova_de_fumaca")),
    "Ciii": ((6.0, "aberta"), (12.0, "protegida"), (math.inf, "prova_de_fumaca")),
    # a coluna D nao tem escada protegida: "Nao aplicavel", e a prova de fumaca
    # comeca em +6 m.
    "D":    ((6.0, "aberta"), (math.inf, "prova_de_fumaca")),
    "E":    ((6.0, "aberta"), (12.0, "protegida"), (math.inf, "prova_de_fumaca")),
}
# "prova_de_fumaca" e' o GRUPO da Tab.11 (9.5.2 c): C i antecamara ventilada,
# C ii pressurizada, C iii externa. Qual dos tres e' decisao de projeto, e o
# tipo declarado tem de ser um deles.
TIPOS_PROVA_DE_FUMACA = ("antecamara_ventilada", "pressurizada", "externa")
TIPOS_DECLARAVEIS = ("aberta", "protegida") + TIPOS_PROVA_DE_FUMACA
# nota e) da Tab.11: escadas externas limitadas a edificios de ate 45 m.
ESCADA_EXTERNA_ALTURA_MAX_M = 45.0
# 7.4.2 / 7.4.3: rota unica.
ROTA_UNICA_CI_ALTURA_MAX_M = 80.0
ROTA_UNICA_DEMAIS_ALTURA_MAX_M = 30.0
# 6.4.2: abandono faseado nao se aplica a edificacao com altura <= 6 m.
FASEADO_ALTURA_MIN_M = 6.0
ESTRATEGIAS_ABANDONO = ("simultaneo", "faseado")


def tipo_escada_exigido(ocupante, altura_m):
    """Tipo de escada/rampa exigido pela Tab.11 (grupo, nao a variante)."""
    if ocupante not in TIPO_ESCADA_TAB11:
        raise ValueError("ocupante %r sem coluna na Tabela 11" % (ocupante,))
    for limite, tipo in TIPO_ESCADA_TAB11[ocupante]:
        if altura_m <= limite + 1e-9:
            return tipo
    return "prova_de_fumaca"


def atende_tipo_escada(declarado, exigido):
    """O tipo declarado atende ao exigido pela Tab.11?

    Um tipo MAIS protegido atende ao menos protegido (uma escada pressurizada
    serve onde a Tab.11 pede protegida); o contrario nao.
    """
    ordem = {"aberta": 0, "protegida": 1}
    for tipo in TIPOS_PROVA_DE_FUMACA:
        ordem[tipo] = 2
    ordem["prova_de_fumaca"] = 2
    if declarado not in ordem or exigido not in ordem:
        raise ValueError("tipo de escada desconhecido: %r / %r"
                         % (declarado, exigido))
    return ordem[declarado] >= ordem[exigido]


class EntradaIncendio(ValueError):
    """A entrada declarada nao permite dimensionar as saidas de emergencia."""


def declarada(spec_incendio) -> bool:
    """Ha o minimo para dimensionar: atividade dos pavimentos e velocidade?

    A pergunta tem UMA resposta, aqui, para que o escopo publicado pelo
    adaptador e o calculo nao usem criterios diferentes.
    """
    if not isinstance(spec_incendio, dict):
        return False
    return bool(spec_incendio.get("pavimentos")
                and spec_incendio.get("velocidade_incendio") is not None)


def _positivo(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor > 0)


def _nao_negativo(valor):
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor) and valor >= 0)


def _valida(spec, contexto):
    """Recusa a entrada malformada em vez de deixar o solver estourar fundo."""
    erros = []
    velocidade = spec.get("velocidade_incendio")
    if velocidade not in VELOCIDADES:
        erros.append("velocidade_incendio deve ser 1, 2, 3 ou 4 (Tabela 2); "
                     "recebido %r. Ela depende da carga de incendio e dos "
                     "materiais e NAO tem default" % (velocidade,))
    declarados = spec.get("pavimentos")
    if not isinstance(declarados, dict) or not declarados:
        erros.append("incendio.pavimentos deve ser um objeto {nome_do_pavimento: "
                     "{...}} cobrindo TODOS os pavimentos da estrutura")
        raise EntradaIncendio("; ".join(erros))
    nomes_estrutura = [p["nome"] for p in contexto["pavimentos"]]
    faltando = [n for n in nomes_estrutura if n not in declarados]
    sobrando = [n for n in declarados if n not in nomes_estrutura]
    if faltando:
        # pavimento omitido do projeto de incendio e' populacao que some do
        # calculo da escada em silencio - o defeito que este framework caca.
        erros.append("estes pavimentos da estrutura nao foram declarados em "
                     "incendio.pavimentos: %s. Um pavimento sem atividade "
                     "declarada tem de ser declarado 'sem_ocupacao': true, "
                     "nunca omitido" % ", ".join(faltando))
    if sobrando:
        erros.append("estes pavimentos declarados em incendio.pavimentos nao "
                     "existem na estrutura: %s" % ", ".join(sobrando))
    for nome, dados in declarados.items():
        if not isinstance(dados, dict):
            erros.append("incendio.pavimentos[%s] deve ser um objeto" % nome)
            continue
        if dados.get("sem_ocupacao"):
            continue
        atividade = dados.get("atividade")
        if atividade not in pop.DENSIDADES:
            erros.append("incendio.pavimentos[%s].atividade %r nao consta da "
                         "Tabela 4" % (nome, atividade))
        for chave in ("areas_excluidas_m2", "areas_incluidas_m2"):
            valor = dados.get(chave)
            if valor is not None and (not isinstance(valor, list)
                                      or not all(_nao_negativo(v) for v in valor)):
                erros.append("incendio.pavimentos[%s].%s deve ser uma lista de "
                             "areas >= 0" % (nome, chave))
    ocupante = spec.get("ocupante")
    if ocupante is not None and ocupante not in OCUPANTES:
        erros.append("ocupante %r nao consta da Tabela 1 (use uma de: %s)"
                     % (ocupante, ", ".join(OCUPANTES)))
    escada = spec.get("escada") or {}
    if not isinstance(escada, dict):
        erros.append("incendio.escada deve ser um objeto")
    else:
        tipo = escada.get("tipo")
        if tipo is not None and tipo not in TIPOS_DECLARAVEIS:
            erros.append("incendio.escada.tipo %r desconhecido (use um de: %s)"
                         % (tipo, ", ".join(TIPOS_DECLARAVEIS)))
        n = escada.get("n_rotas_verticais")
        if n is not None and (not isinstance(n, int) or isinstance(n, bool)
                              or n < 1):
            erros.append("incendio.escada.n_rotas_verticais deve ser inteiro >= 1")
    estrategia = spec.get("estrategia_abandono", "simultaneo")
    if estrategia not in ESTRATEGIAS_ABANDONO:
        erros.append("estrategia_abandono deve ser uma de %s"
                     % (list(ESTRATEGIAS_ABANDONO),))
    if erros:
        raise EntradaIncendio("; ".join(erros))


def _populacao_dos_pavimentos(spec, contexto):
    """Populacao pavimento a pavimento (Tab.4), do topo para a base."""
    declarados = spec["pavimentos"]
    politica = spec.get("politica_arredondamento",
                        pop.POLITICA_ARREDONDAMENTO_PADRAO)
    area_bruta = contexto["area_pavimento_m2"]
    n = len(contexto["pavimentos"])
    linhas = []
    for i, pav in enumerate(contexto["pavimentos"]):
        nome = pav["nome"]
        dados = declarados[nome]
        # o pavimento mais baixo da lista e' o 1o andar acima da descarga; a
        # lista vem do TOPO para a BASE (contrato do G3).
        andar = n - i
        if dados.get("sem_ocupacao"):
            linhas.append({"nome": nome, "andar": andar, "ocupado": False,
                           "populacao": 0, "populacao_exata": 0.0,
                           "atividade": None,
                           "motivo": dados.get("motivo",
                                               "declarado sem ocupacao humana")})
            continue
        excluidas = list(dados.get("areas_excluidas_m2") or [])
        incluidas = list(dados.get("areas_incluidas_m2") or [])
        area = dados.get("area_computavel_m2")
        if area is None:
            area = area_bruta - math.fsum(excluidas) + math.fsum(incluidas)
        try:
            r = pop.populacao(
                dados["atividade"],
                area_computavel_m2=(area if area > 0 else None),
                dormitorios=dados.get("dormitorios"),
                vagas=dados.get("vagas"),
                area_alojamento_m2=dados.get("area_alojamento_m2"),
                assentos_fixos=dados.get("assentos_fixos"),
                politica_arredondamento=politica)
        except ValueError as exc:
            raise EntradaIncendio("pavimento %s: %s" % (nome, exc)) from exc
        linhas.append({
            "nome": nome, "andar": andar, "ocupado": True,
            "atividade": dados["atividade"], "criterio": r["criterio"],
            # a area so ENTRA na conta quando a Tab.4 mede a atividade por area:
            # habitacao e' medida por dormitorio e garagem por vaga, e cobrar
            # exclusao de area nesses casos seria aviso sem consequencia.
            "area_entra_na_conta": "por_area" in r["densidade"],
            "area_declarada": dados.get("area_computavel_m2") is not None,
            "populacao": r["populacao"], "populacao_exata": r["populacao_exata"],
            "area_computavel_m2": round(float(area), 2),
            "areas_excluidas_m2": excluidas, "areas_incluidas_m2": incluidas,
            "politica_arredondamento": r["politica_arredondamento"],
        })
    return linhas


def _ocupante(spec, linhas):
    """Classe do ocupante: declarada, ou derivada dos EXEMPLOS da Tab.1.

    4.4.1: ocupacao diversificada projeta pelo requisito MAIS RESTRITIVO. A
    ordem de restricao usada e' a da propria Tab.11 (a coluna que exige a
    escada mais protegida na menor altura).
    """
    if spec.get("ocupante"):
        return spec["ocupante"], "declarado no spec"
    atividades = [linha["atividade"] for linha in linhas if linha["ocupado"]]
    derivados = []
    sem_mapa = []
    for atividade in atividades:
        if atividade in OCUPANTE_POR_ATIVIDADE:
            derivados.append(OCUPANTE_POR_ATIVIDADE[atividade])
        else:
            sem_mapa.append(atividade)
    if sem_mapa:
        raise EntradaIncendio(
            "a classe do ocupante (Tabela 1) nao e' derivavel da(s) atividade(s) "
            "%s: a Tab.1 nao as nomeia entre os seus exemplos. Declare "
            "incendio.ocupante" % ", ".join(sorted(set(sem_mapa))))
    if not derivados:
        raise EntradaIncendio("nenhum pavimento ocupado: nao ha populacao a "
                              "abandonar, e a rota de saida nao faz sentido")
    # mais restritivo = o que a Tab.11 obriga a escada mais protegida antes
    ordem = sorted(set(derivados),
                   key=lambda o: TIPO_ESCADA_TAB11[o][0][0])
    escolhido = ordem[0]
    nota = ("derivado dos exemplos da Tabela 1 a partir da(s) atividade(s) "
            "declarada(s); 4.4.1 - adotado o mais restritivo entre %s"
            % ", ".join(sorted(set(derivados))))
    return escolhido, nota


def _altura_edificacao(spec, linhas, pe_direito):
    """Altura da edificacao (3.3): da descarga ao piso ocupado mais elevado.

    NOTA 2 de 3.3: areas tecnicas acima do ultimo pavimento ocupado (barrilete,
    casa de maquinas) NAO entram. Por isso a altura le a lista de pavimentos
    OCUPADOS, e nao o H_total da estrutura - uma cobertura de manutencao
    declarada 'sem_ocupacao' nao pode empurrar o predio para outra linha da
    Tabela 11.
    """
    if spec.get("altura_edificacao_m") is not None:
        if not _positivo(spec["altura_edificacao_m"]):
            raise EntradaIncendio("altura_edificacao_m deve ser > 0")
        return float(spec["altura_edificacao_m"]), "declarada no spec"
    ocupados = [linha for linha in linhas if linha["ocupado"]]
    if not ocupados:
        raise EntradaIncendio("nenhum pavimento ocupado para medir a altura")
    andar = max(linha["andar"] for linha in ocupados)
    return (andar * pe_direito,
            "derivada: %d andares acima da descarga x pe-direito de %.2f m "
            "(3.3 NOTA 2 - areas tecnicas acima do ultimo pavimento ocupado "
            "nao entram)" % (andar, pe_direito))


def _largura_escada(spec, linhas, perfil, andar_mais_elevado, estrategia):
    """Largura minima exigida para a saida vertical (9.4.3 / 9.4.4 + 9050)."""
    w_pessoa = largura_pessoa_vertical_mm(perfil, andar_mais_elevado)
    ocupados = [linha for linha in linhas if linha["ocupado"]]
    if estrategia == "faseado":
        # 9.4.4: largura por pessoa da COLUNA DO SEGUNDO ANDAR (nota F) vezes a
        # populacao dos DOIS pavimentos de maior lotacao.
        w_pessoa = largura_pessoa_vertical_mm(perfil, COLUNA_ABANDONO_FASEADO)
        maiores = sorted((linha["populacao"] for linha in ocupados),
                         reverse=True)[:2]
        base = sum(maiores)
        criterio = ("9.4.4 - abandono faseado: coluna do 2o andar da Tab.10 x a "
                    "populacao dos dois pavimentos de maior lotacao")
    else:
        # 9.4.3: largura por pessoa do piso mais elevado ocupado x populacao
        # TOTAL do edificio, EXCLUINDO a populacao do terreo.
        base = sum(linha["populacao"] for linha in ocupados)
        criterio = ("9.4.3 - abandono simultaneo: Tab.10 no piso mais elevado "
                    "ocupado x populacao total, excluida a do terreo (a lista de "
                    "pavimentos comeca acima da descarga)")
    calculada_m = base * w_pessoa / 1000.0
    exigida_m = max(calculada_m, ESCADA_LARGURA_MIN_M)
    return {
        "estrategia": estrategia,
        "largura_por_pessoa_mm": w_pessoa,
        "populacao_de_calculo": base,
        "largura_calculada_m": round(calculada_m, 3),
        "largura_minima_9050_m": ESCADA_LARGURA_MIN_M,
        "largura_exigida_m": round(exigida_m, 3),
        "governa": ("NBR 9050 6.8.3" if exigida_m > calculada_m + 1e-9
                    else "NBR 9077 Tab.10"),
        "criterio": criterio,
    }


def _geometria_9050(escada):
    """Confere a geometria da escada declarada contra a NBR 9050 6.8.2/6.8.7.

    A escada de emergencia e' rota acessivel: a faixa de piso/espelho da 9050
    (0,28-0,32 / 0,16-0,18) e' mais estreita que a de `escada_concreto`
    (0,25-0,32), que foi escrita quando a 9050 estava fora do acervo. Uma
    escada que passa no gate estrutural pode NAO servir de rota de saida, e e'
    esta a conferencia que diz isso em voz alta.
    """
    if not isinstance(escada, dict) or not escada.get("geometria"):
        return None
    geo = escada["geometria"]
    piso = float(geo["piso"])
    espelho = float(geo["espelho"])
    blondel = float(geo.get("blondel", piso + 2.0 * espelho))
    ok_piso = PISO_9050_M[0] - 1e-9 <= piso <= PISO_9050_M[1] + 1e-9
    ok_espelho = ESPELHO_9050_M[0] - 1e-9 <= espelho <= ESPELHO_9050_M[1] + 1e-9
    ok_blondel = BLONDEL_9050_M[0] - 1e-9 <= blondel <= BLONDEL_9050_M[1] + 1e-9
    return {
        "piso_m": round(piso, 4), "espelho_m": round(espelho, 4),
        "blondel_m": round(blondel, 4),
        "piso_faixa_m": list(PISO_9050_M),
        "espelho_faixa_m": list(ESPELHO_9050_M),
        "blondel_faixa_m": list(BLONDEL_9050_M),
        "ok_piso": bool(ok_piso), "ok_espelho": bool(ok_espelho),
        "ok_blondel": bool(ok_blondel),
        "OK": bool(ok_piso and ok_espelho and ok_blondel),
        "referencia": "NBR 9050:2020 6.8.2",
    }


def _sistemas(spec, contexto, altura_m, area_total_m2):
    """Os quatro sistemas exigidos por 4.4.2 e 13.1-13.3, ja aferidos.

    O edificio nao e' um galpao: os modulos dimensionam UM pavimento (C x L), e o
    total do predio e' o do pavimento vezes o numero de pavimentos - exceto a
    RESERVA de incendio dos hidrantes, que e' UMA para o predio inteiro e nao se
    multiplica.
    """
    import deteccao_alarme_nbr17240 as da
    import iluminacao_emergencia_nbr10898 as ie
    import sinalizacao_nbr16820 as sn

    C = contexto["C"]
    L = contexto["L"]
    pe = contexto["pe_direito"]
    n_pav = len(contexto["pavimentos"])

    ie_spec = dict(spec.get("iluminacao_emergencia") or {})
    ie_spec.update({"C": C, "L": L, "pe_direito": pe})
    emerg = ie.dimensiona_iluminacao_emergencia(ie_spec)

    sn_spec = dict(spec.get("sinalizacao") or {})
    sn_spec.update({"C": C, "L": L})
    sinal = sn.dimensiona_sinalizacao(sn_spec)

    da_spec = dict(spec.get("deteccao") or {})
    da_spec.update({"C": C, "L": L})
    da_spec.setdefault("altura_teto", pe)
    alarme = da.dimensiona_deteccao_alarme(da_spec)

    hidr = None
    if spec.get("hidrantes"):
        import hidrantes_nbr13714 as hd
        hd_spec = dict(spec["hidrantes"])
        # `dimensiona_hidrantes` so consulta a Tab.D.1 quando 'tipo' NAO e'
        # declarado: com o tipo forcado, uma ocupacao inexistente atravessa sem
        # ruido (e a vazao especifica da D.1 - 80 L/min para residencial - se
        # perde em silencio). A ocupacao e' conferida aqui de qualquer jeito.
        ocupacao = hd_spec.get("ocupacao")
        if ocupacao is not None:
            tipo_d1, vazao_d1 = hd.tipo_por_ocupacao(ocupacao)
            if hd_spec.get("tipo") is None:
                hd_spec["tipo"] = tipo_d1
                if vazao_d1 is not None:
                    hd_spec.setdefault("vazao_saida", vazao_d1)
        hd_spec.update({"C": C, "L": L, "altura_m": altura_m})
        hidr = hd.dimensiona_hidrantes(hd_spec)
    return {
        "iluminacao_emergencia": emerg,
        "sinalizacao": sinal,
        "deteccao_alarme": alarme,
        "hidrantes": hidr,
        "por_pavimento": {
            "blocos_autonomos": emerg["N_blocos_total"],
            "placas": sinal["N_total"],
            "detectores": alarme["N_detectores"],
            "acionadores": alarme["N_acionadores"],
            "hidrantes": None if hidr is None else hidr["N_hidrantes"],
        },
        "totais_edificio": {
            "n_pavimentos": n_pav,
            "area_construida_m2": round(area_total_m2, 2),
            "blocos_autonomos": emerg["N_blocos_total"] * n_pav,
            "placas": sinal["N_total"] * n_pav,
            "detectores": alarme["N_detectores"] * n_pav,
            "acionadores": alarme["N_acionadores"] * n_pav,
            "hidrantes": None if hidr is None else hidr["N_hidrantes"] * n_pav,
            # a reserva NAO se multiplica: e' um unico volume de incendio.
            "reserva_incendio_m3": None if hidr is None
                                   else hidr["reserva_incendio_m3"],
        },
    }


def dimensiona(spec_incendio, contexto):
    """Saidas de emergencia do edificio (NBR 9077:2025) e os sistemas de 4.4.2.

    spec_incendio: {
      'velocidade_incendio': 1..4 (Tab.2) - SEM default;
      'pavimentos': {nome: {'atividade' (Tab.4), 'dormitorios'|'vagas'|
                    'area_computavel_m2', 'areas_excluidas_m2',
                    'areas_incluidas_m2'} ou {'sem_ocupacao': True}};
      'ocupante'   : opc, classe da Tab.1 (derivada da atividade se ausente);
      'estrategia_abandono': 'simultaneo' (default) | 'faseado';
      'altura_edificacao_m': opc (3.3; derivada dos pavimentos ocupados);
      'escada'     : {'tipo' (9.5.2), 'n_rotas_verticais'};
      'caminhamento': {'unica_direcao_m', 'alternativas_m', 'leiaute_definido',
                       'controle_fumaca'} - MEDIDAS na planta, declaradas;
      'rotas_horizontais': {'largura_declarada_m', 'uso_publico'};
      'iluminacao_emergencia'|'sinalizacao'|'deteccao'|'hidrantes': opc,
                    repassados aos modulos ja aferidos.
    }
    contexto: {'pavimentos' (topo->base, com 'nome'), 'C', 'L', 'pe_direito',
               'area_pavimento_m2', 'escada' (resultado de escada_concreto, ou
               None)}.
    """
    if not isinstance(spec_incendio, dict):
        raise EntradaIncendio("incendio deve ser um objeto JSON")
    _valida(spec_incendio, contexto)

    linhas = _populacao_dos_pavimentos(spec_incendio, contexto)
    ocupante, nota_ocupante = _ocupante(spec_incendio, linhas)
    velocidade = spec_incendio["velocidade_incendio"]
    try:
        perfil = perfil_risco(ocupante, velocidade)
    except ValueError as exc:
        raise EntradaIncendio(str(exc)) from exc
    altura_m, nota_altura = _altura_edificacao(spec_incendio, linhas,
                                               contexto["pe_direito"])
    ocupados = [linha for linha in linhas if linha["ocupado"]]
    andar_mais_elevado = max(linha["andar"] for linha in ocupados)
    pop_total = sum(linha["populacao"] for linha in ocupados)
    pop_critica = max(linha["populacao"] for linha in ocupados)

    estrategia = spec_incendio.get("estrategia_abandono", "simultaneo")
    avisos = []
    if estrategia == "faseado" and altura_m <= FASEADO_ALTURA_MIN_M + 1e-9:
        raise EntradaIncendio(
            "6.4.2: o abandono faseado nao se aplica a edificacoes com altura "
            "menor ou igual a %.0f m (altura declarada/derivada: %.2f m)"
            % (FASEADO_ALTURA_MIN_M, altura_m))

    escada_spec = spec_incendio.get("escada") or {}
    caminhamento = spec_incendio.get("caminhamento") or {}
    horizontais = spec_incendio.get("rotas_horizontais") or {}

    # ---------------------------------------------------------------- ROTAS
    n_min = rotas_minimas(pop_critica)
    n_declarado = escada_spec.get("n_rotas_verticais")
    limite_rota_unica = (ROTA_UNICA_CI_ALTURA_MAX_M if ocupante == "Ci"
                         else ROTA_UNICA_DEMAIS_ALTURA_MAX_M)
    if n_min == 1 and altura_m > limite_rota_unica + 1e-9:
        # 7.4.2/7.4.3: acima do limite de altura a rota unica deixa de ser
        # admitida mesmo com populacao pequena.
        n_min = 2
        avisos.append({
            "code": "rota_unica_vedada_pela_altura",
            "detail": "a populacao por pavimento (%d) admitiria rota unica pela "
                      "Tabela 5, mas 7.4.%s veda rota unica para ocupante %s "
                      "acima de %.0f m (altura %.2f m): o minimo passa a 2"
                      % (pop_critica, "2" if ocupante == "Ci" else "3",
                         ocupante, limite_rota_unica, altura_m)})
    gate_rotas = {"OK": bool(n_declarado is not None and n_declarado >= n_min),
                  "n_minimo": n_min, "n_declarado": n_declarado,
                  "populacao_critica_pavimento": pop_critica,
                  "referencia": "NBR 9077:2025 Tab.5 / 7.4"}
    if n_declarado is None:
        gate_rotas["erro"] = ("incendio.escada.n_rotas_verticais nao declarado: "
                              "o numero de escadas e' decisao de projeto e nao "
                              "e' arbitrado aqui")

    # ------------------------------------------------------- LARGURA VERTICAL
    largura = _largura_escada(spec_incendio, linhas, perfil, andar_mais_elevado,
                              estrategia)
    escada_estrutural = contexto.get("escada")
    largura_declarada = None
    if isinstance(escada_estrutural, dict):
        largura_declarada = escada_estrutural.get("largura_m")
    gate_largura = {
        "OK": bool(largura_declarada is not None
                   and largura_declarada >= largura["largura_exigida_m"] - 1e-9),
        "largura_declarada_m": largura_declarada,
        "fonte_da_largura": "estrutura.escada.largura (declaracao unica)",
        "referencia": "NBR 9077:2025 9.4 Tab.10 + NBR 9050:2020 6.8.3",
    }
    gate_largura.update(largura)
    if largura_declarada is None:
        gate_largura["erro"] = (
            "a escada nao foi declarada em estrutura.escada: a largura que a "
            "NBR 9077 exige e' verificada contra a MESMA declaracao que a "
            "estrutura dimensiona. Este modulo nao cria uma segunda escada")

    # ---------------------------------------------------------- TIPO DE ESCADA
    tipo_exigido = tipo_escada_exigido(ocupante, altura_m)
    tipo_declarado = escada_spec.get("tipo")
    gate_tipo = {
        "OK": bool(tipo_declarado is not None
                   and atende_tipo_escada(tipo_declarado, tipo_exigido)),
        "tipo_exigido": tipo_exigido, "tipo_declarado": tipo_declarado,
        "altura_edificacao_m": round(altura_m, 2), "ocupante": ocupante,
        "referencia": "NBR 9077:2025 Tab.11",
    }
    if tipo_declarado is None:
        gate_tipo["erro"] = ("incendio.escada.tipo nao declarado; a Tab.11 exige "
                             "'%s' para ocupante %s a %.2f m"
                             % (tipo_exigido, ocupante, altura_m))
    elif (tipo_declarado == "externa"
          and altura_m > ESCADA_EXTERNA_ALTURA_MAX_M + 1e-9):
        gate_tipo["OK"] = False
        gate_tipo["erro"] = ("nota e) da Tab.11: escadas externas sao limitadas a "
                             "edificios de ate %.0f m (altura %.2f m)"
                             % (ESCADA_EXTERNA_ALTURA_MAX_M, altura_m))
    if tipo_exigido == "prova_de_fumaca":
        avisos.append({
            "code": "ventilacao_da_escada_nao_dimensionada",
            "detail": "a Tab.11 exige escada A PROVA DE FUMACA: antecamara "
                      "ventilada, pressurizacao (NBR 14880) ou escada externa. "
                      "Este modulo diz QUAL tipo e' exigido e NAO dimensiona a "
                      "ventilacao, o duto nem a pressurizacao"})

    # ------------------------------------------------- GEOMETRIA DA ESCADA
    gate_geometria = _geometria_9050(escada_estrutural)

    # ------------------------------------------------------- CAMINHAMENTO
    # O ganho de 15 % da Tab.7 e' o do sistema de DETECCAO (NBR 17240), nao o do
    # alarme MANUAL que 4.4.2 c) ja exige de toda edificacao. Confundir os dois
    # daria 15 % de distancia de graca a todo predio; por isso o ganho so entra
    # quando o projeto DECLARA a deteccao automatica.
    deteccao_automatica = bool(caminhamento.get("deteccao_automatica"))
    if deteccao_automatica and _FAMILIA[ocupante] == "B" \
            and not caminhamento.get("comunicacao_por_voz"):
        # NOTA 2 da Tab.7: para o perfil B o ganho so vale com comunicacao de
        # emergencia por voz.
        deteccao_automatica = False
        avisos.append({
            "code": "ganho_de_deteccao_negado_perfil_b",
            "detail": "NOTA 2 da Tab.7: para os perfis de risco 'B' o ganho de "
                      "caminhamento por deteccao e alarme so e' permitido se o "
                      "sistema incluir comunicacao de emergencia por voz, que "
                      "nao foi declarada: o ganho de 15 % foi retirado"})
    limites = distancia_maxima(
        perfil, pe_direito_rota_m=contexto["pe_direito"],
        deteccao=deteccao_automatica,
        controle_fumaca=bool(caminhamento.get("controle_fumaca")),
        leiaute_definido=bool(caminhamento.get("leiaute_definido", True)))
    d_unica = caminhamento.get("unica_direcao_m")
    d_alt = caminhamento.get("alternativas_m")
    ok_unica = d_unica is None or d_unica <= limites["unica_direcao_m"] + 1e-9
    ok_alt = d_alt is None or d_alt <= limites["alternativas_m"] + 1e-9
    gate_caminhamento = {
        "OK": bool(ok_unica and ok_alt
                   and (d_unica is not None or d_alt is not None)),
        "declarado_unica_direcao_m": d_unica,
        "declarado_alternativas_m": d_alt,
        "referencia": "NBR 9077:2025 Tab.6 + Tab.7",
    }
    gate_caminhamento.update(limites)
    if d_unica is None and d_alt is None:
        gate_caminhamento["erro"] = (
            "incendio.caminhamento nao declara distancia nenhuma: as distancias "
            "a percorrer sao MEDIDAS na planta de arquitetura, que este "
            "framework nao tem para o edificio, e nao podem ser estimadas pelo "
            "envelope estrutural")

    # ------------------------------------------- LARGURA DAS ROTAS HORIZONTAIS
    w_pessoa_h = LARGURA_PESSOA_HORIZ_MM[perfil]
    calc_h = pop_critica * w_pessoa_h / 1000.0
    if horizontais.get("uso_publico"):
        min_9050 = CORREDOR_USO_PUBLICO_MIN_M
    else:
        extensao = horizontais.get("extensao_m", math.inf)
        min_9050 = next(v for limite, v in CORREDOR_MIN_M if extensao <= limite)
    exigida_h = max(calc_h, min_9050)
    largura_h_declarada = horizontais.get("largura_declarada_m")
    gate_horizontais = {
        "OK": bool(largura_h_declarada is not None
                   and largura_h_declarada >= exigida_h - 1e-9),
        "largura_por_pessoa_mm": w_pessoa_h,
        "populacao_de_calculo": pop_critica,
        "largura_calculada_m": round(calc_h, 3),
        "largura_minima_9050_m": min_9050,
        "largura_exigida_m": round(exigida_h, 3),
        "largura_declarada_m": largura_h_declarada,
        "governa": ("NBR 9050 6.11.1" if exigida_h > calc_h + 1e-9
                    else "NBR 9077 Tab.8"),
        "referencia": "NBR 9077:2025 7.5.6.4 Tab.8 + NBR 9050:2020 6.11.1",
    }
    if largura_h_declarada is None:
        gate_horizontais["erro"] = (
            "incendio.rotas_horizontais.largura_declarada_m nao declarada: a "
            "largura do corredor e das portas de ingresso na escada (7.5.6.5) "
            "e' medida na planta de arquitetura")

    # ----------------------------------------------------------- SISTEMAS
    area_total = contexto["area_pavimento_m2"] * len(contexto["pavimentos"])
    sistemas = _sistemas(spec_incendio, contexto, altura_m, area_total)

    gates = {
        "populacao": {"OK": True, "total_edificio": pop_total,
                      "critica_por_pavimento": pop_critica,
                      "perfil_risco": perfil, "ocupante": ocupante,
                      "velocidade_incendio": velocidade,
                      "referencia": "NBR 9077:2025 Tab.1/2/3/4"},
        "rotas_verticais": gate_rotas,
        "escada_largura": gate_largura,
        "escada_tipo": gate_tipo,
        "caminhamento": gate_caminhamento,
        "rotas_horizontais": gate_horizontais,
        "iluminacao_emergencia": {
            "OK": sistemas["iluminacao_emergencia"]["OK"],
            "N_por_pavimento": sistemas["iluminacao_emergencia"]["N_blocos_total"],
            "autonomia_h": sistemas["iluminacao_emergencia"]["autonomia_h"],
            "referencia": "NBR 10898 (4.4.2 b)"},
        "sinalizacao": {
            "OK": sistemas["sinalizacao"]["OK"],
            "N_por_pavimento": sistemas["sinalizacao"]["N_total"],
            "placa_lado_mm": sistemas["sinalizacao"]["placa_lado_mm"],
            "referencia": "NBR 16820 (4.4.2 a)"},
        "deteccao_alarme": {
            "OK": sistemas["deteccao_alarme"]["OK"],
            "N_detectores_por_pavimento": sistemas["deteccao_alarme"]["N_detectores"],
            "N_acionadores_por_pavimento": sistemas["deteccao_alarme"]["N_acionadores"],
            "referencia": "NBR 17240 (4.4.2 c)"},
    }
    if gate_geometria is not None:
        gates["escada_geometria"] = gate_geometria
    if sistemas["hidrantes"] is not None:
        gates["hidrantes"] = {
            "OK": sistemas["hidrantes"]["OK"],
            "tipo": sistemas["hidrantes"]["tipo"],
            "N_por_pavimento": sistemas["hidrantes"]["N_hidrantes"],
            "reserva_incendio_m3": sistemas["hidrantes"]["reserva_incendio_m3"],
            "referencia": "NBR 13714"}

    if estrategia == "faseado":
        avisos.append({
            "code": "abandono_faseado_exige_gestao",
            "detail": "6.4.2: o abandono faseado so e' admitido com escada a "
                      "prova de fumaca, halls de elevador compartimentados, "
                      "plano de abandono, brigada treinada, alarme setorizado "
                      "por pavimento e plano de gestao (Anexo A). NADA disso e' "
                      "verificado por calculo aqui"})
    reprovados = sorted(k for k, g in gates.items() if not g["OK"])
    return {
        "perfil_risco": perfil, "ocupante": ocupante,
        "ocupante_proveniencia": nota_ocupante,
        "velocidade_incendio": velocidade,
        "velocidade_criterio": VELOCIDADES[velocidade]["criterio"],
        "estrategia_abandono": estrategia,
        "altura_edificacao_m": round(altura_m, 2),
        "altura_proveniencia": nota_altura,
        "andar_mais_elevado_ocupado": andar_mais_elevado,
        "populacao_por_pavimento": linhas,
        "populacao_total": pop_total,
        "sistemas": sistemas,
        "gates": gates, "reprovados": reprovados,
        "ATENDE": not reprovados,
        "escopo": _escopo(tipo_exigido, estrategia),
        "avisos": avisos + _avisos(spec_incendio, linhas, gate_geometria),
    }


def _escopo(tipo_exigido, estrategia):
    return {
        "populacao_nbr9077": "implemented",
        "rotas_verticais": "implemented",
        "rotas_horizontais": "partial",       # largura verificada, leiaute nao
        "distancia_a_percorrer": "partial",   # verificada, nao medida
        "iluminacao_emergencia": "implemented",
        "sinalizacao": "implemented",
        "deteccao_alarme": "implemented",
        # o que NAO e' calculado aqui, nomeado em vez de omitido:
        "ventilacao_da_escada": ("not_available"
                                 if tipo_exigido == "prova_de_fumaca"
                                 else "not_applicable"),
        "antecamara_pressurizacao_nbr14880": (
            "not_available" if tipo_exigido == "prova_de_fumaca"
            else "not_applicable"),
        "compartimentacao_e_trrf": "not_available",
        "area_de_refugio_nbr9050": "not_available",
        "abandono_horizontal_progressivo": "not_available",
        "plano_de_gestao_anexo_a": ("not_available" if estrategia == "faseado"
                                    else "not_claimed"),
        "leiaute_arquitetonico": "not_available",
        "aprovacao_legal": "not_claimed",
        "avcb": "not_claimed",
        "construction_readiness": "not_claimed",
    }


def _avisos(spec, linhas, gate_geometria):
    avisos = []
    sem_exclusao = sorted(
        linha["nome"] for linha in linhas
        if linha["ocupado"] and linha.get("area_entra_na_conta")
        and not linha.get("area_declarada")
        and not linha.get("areas_excluidas_m2"))
    if sem_exclusao:
        # 5.1.1 manda EXCLUIR escada, antecamara, poco de elevador, shafts,
        # areas tecnicas e sanitarios. Exclusao zero num predio real e' lacuna
        # de projeto, e ela infla a populacao (conservador) - mas o silencio
        # nao pode passar por conferencia.
        avisos.append({
            "code": "area_computavel_sem_exclusoes",
            "pavimentos": sem_exclusao,
            "detail": "5.1.1 manda excluir da area computavel a circulacao "
                      "vertical protegida, o poco do elevador, shafts, areas "
                      "tecnicas e sanitarios. Estes pavimentos nao declararam "
                      "areas_excluidas_m2 e usaram a area BRUTA do envelope "
                      "estrutural: %s" % ", ".join(sem_exclusao)})
    if gate_geometria is not None and not gate_geometria["OK"]:
        avisos.append({
            "code": "geometria_da_escada_fora_da_nbr9050",
            "detail": "a escada declarada tem piso/espelho fora da faixa da NBR "
                      "9050 6.8.2 (piso %.3f m, espelho %.3f m): serve como "
                      "escada, nao como ROTA ACESSIVEL de saida"
                      % (gate_geometria["piso_m"], gate_geometria["espelho_m"])})
    avisos.append({
        "code": "distancias_e_larguras_sao_declaradas",
        "detail": "as distancias a percorrer e as larguras de corredor sao "
                  "MEDIDAS na planta de arquitetura e aqui apenas VERIFICADAS. "
                  "O framework nao tem a planta de arquitetura do edificio"})
    return avisos


def relatorio_pt(resultado):
    """Quadro das saidas de emergencia, um pavimento por linha."""
    linhas = [
        "SAIDAS DE EMERGENCIA - ABNT NBR 9077:2025",
        "CONCEITUAL - PENDENTE REVISAO E ART DO ENG. RESPONSAVEL",
        "  Ocupante: %s (%s)" % (resultado["ocupante"],
                                 resultado["ocupante_proveniencia"]),
        "  Velocidade de crescimento do incendio: %d (%s)"
        % (resultado["velocidade_incendio"],
           VELOCIDADES[resultado["velocidade_incendio"]]["nome"]),
        "  Perfil de risco de vida (Tab.3): %s" % resultado["perfil_risco"],
        "  Altura da edificacao: %.2f m (%s)" % (resultado["altura_edificacao_m"],
                                                 resultado["altura_proveniencia"]),
        "  Estrategia de abandono: %s" % resultado["estrategia_abandono"],
        "",
        "  %-14s %6s %-26s %10s" % ("pavimento", "andar", "atividade", "pessoas"),
        "  " + "-" * 60,
    ]
    for linha in resultado["populacao_por_pavimento"]:
        linhas.append("  %-14s %6d %-26s %10s"
                      % (linha["nome"], linha["andar"],
                         linha["atividade"] or "(sem ocupacao)",
                         linha["populacao"]))
    linhas.append("  " + "-" * 60)
    linhas.append("  Populacao total (acima da descarga): %d pessoas"
                  % resultado["populacao_total"])
    linhas.append("")
    g = resultado["gates"]
    linhas.append("  Escada: exigida %.2f m (%s), declarada %s m"
                  % (g["escada_largura"]["largura_exigida_m"],
                     g["escada_largura"]["governa"],
                     g["escada_largura"]["largura_declarada_m"]))
    linhas.append("  Tipo exigido (Tab.11): %s ; declarado: %s"
                  % (g["escada_tipo"]["tipo_exigido"],
                     g["escada_tipo"]["tipo_declarado"]))
    linhas.append("  Rotas verticais: minimo %d, declaradas %s"
                  % (g["rotas_verticais"]["n_minimo"],
                     g["rotas_verticais"]["n_declarado"]))
    linhas.append("  Distancia maxima: %.1f m (alternativas) / %.1f m (uma "
                  "direcao)" % (g["caminhamento"]["alternativas_m"],
                                g["caminhamento"]["unica_direcao_m"]))
    linhas.append("")
    linhas.append("  Gate: %s%s" % ("ATENDE" if resultado["ATENDE"] else "REPROVA",
                                    "" if resultado["ATENDE"] else
                                    " (%s)" % ", ".join(resultado["reprovados"])))
    for aviso in resultado["avisos"]:
        linhas.append("  [aviso] %s" % aviso["detail"])
    return "\n".join(linhas)
