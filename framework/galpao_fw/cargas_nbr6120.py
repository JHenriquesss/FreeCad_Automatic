# ============================================================================
# cargas_nbr6120.py - O QUE ESTE SCRIPT FAZ / FORNECE
# Tabelas de ACOES da ABNT NBR 6120:2019 (Acoes para o calculo de estruturas de
# edificacoes), que ate aqui o framework nao tinha: cada modulo chutava a sua
# carga de uso ou recebia o peso da parede como entrada do usuario. E a base da
# DESCIDA DE CARGAS do edificio multipavimento (G3) - tudo o mais consome daqui.
#   1) Tabela 1  - pesos especificos aparentes dos materiais (kN/m3).
#   2) Tabela 2  - ALVENARIAS: peso do painel de parede em kN/m2 POR M2 DE PAREDE
#      (nao kN/m3), ja incluindo o revestimento de 0, 1 ou 2 cm POR FACE, separando
#      alvenaria ESTRUTURAL de alvenaria de VEDACAO.
#   3) Tabela 3  - divisorias e caixilhos (drywall, retrateis, caixilhos).
#   4) Tabela 10 - cargas variaveis de uso por ambiente (kN/m2 + concentrada kN),
#      com a marca de REDUTIVEL/NAO REDUTIVEL de cada linha (nota "a" da tabela).
#   5) Tabela 11 - paredes divisorias SEM POSICAO DEFINIDA (carga adicional), com
#      o "NAO PERMITIDO" acima de 3,0 kN/m e a dispensa para q >= 4,0 kN/m2.
#   6) Tabela 12 - forcas horizontais em guarda-corpos e barreiras (kN/m, a 1,1 m
#      acima do piso acabado) + ancoragem de balancim Fd = 15 kN (6.3).
#   7) Tabela 13 - garagens categoria I (veiculos ate 30 kN).
#   8) Tabela 19 / item 6.12 - multiplicador alpha_n de reducao das cargas
#      variaveis na descida de cargas para PILARES E FUNDACOES (nao para vigas
#      nem lajes), por grupo de pisos adjacentes de mesmo uso.
#
# PROVENIENCIA: todos os numeros foram transcritos do texto da norma via
# NotebookLM (notebook "04 Acoes e Equipamentos", fonte NBR 6120:2019), com as
# citacoes do texto bruto conferidas - NAO de memoria. Regra do projeto apos o
# episodio do "AR300" inventado: sem fonte, nao se escreve o numero.
#
# CONFERENCIA INDEPENDENTE DA TABELA 2 (rotulo x geometria): a NOTA da tabela
# declara revestimento de 19 kN/m3, logo 1 cm por face deve somar 2*0,01*19 =
# 0,38 kN/m2 (0,4 apos arredondamento a 1 decimal). Todas as linhas fecham nisso,
# EXCETO o bloco ceramico de furo horizontal de 9 cm (1,1 -> 1,6) e de 19 cm
# (1,8 -> 2,3), onde o salto tabelado e 0,5. Conferido contra o texto bruto da
# fonte: os digitos impressos na norma sao mesmo 1,6 e 2,3 - e arredondamento da
# propria norma, nao erro de leitura. Transcritos como estao (ver _coerencia_tab2).
#
# Unidades: m, kN. Saidas em portugues.
# ============================================================================
"""Acoes da NBR 6120:2019: pesos proprios (Tab.1/2/3), cargas variaveis de uso
(Tab.10), paredes sem posicao definida (Tab.11), guarda-corpos (Tab.12), garagens
(Tab.13) e reducao de cargas variaveis na descida de cargas (Tab.19 / 6.12)."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tabela 1 - pesos especificos aparentes (kN/m3). Subconjunto usado pelo
# framework; onde a norma da uma faixa, o valor entre parenteses e o medio.
# ---------------------------------------------------------------------------
PESO_ESPECIFICO = {
    "concreto_simples": 24.0,
    "concreto_armado": 25.0,
    "argamassa_cimento_areia": 21.0,      # faixa 19 a 23, medio 21
    "madeira_laminada_colada": 5.0,
    "mdf": 8.0,
    "osb": 7.0,
}

# ---------------------------------------------------------------------------
# Tabela 2 - ALVENARIAS. peso em kN/m2 DE PAINEL DE PAREDE (nao por m3), para
# espessura de revestimento por face de 0, 1 e 2 cm.
# NOTA da norma: argamassa de assentamento de 1 cm a 19 kN/m3; revestimento a
# 19 kN/m3; um meio bloco para cada tres blocos inteiros; SEM graute.
# ---------------------------------------------------------------------------
REVESTIMENTOS_CM = (0.0, 1.0, 2.0)

ALVENARIAS = {
    # --- ALVENARIA ESTRUTURAL ---
    "bloco_concreto_estrutural": {
        "nome": "Bloco de concreto vazado (classes A e B, NBR 6136)",
        "estrutural": True,
        "pesos": {14.0: (2.0, 2.3, 2.7), 19.0: (2.7, 3.0, 3.4)},
    },
    "bloco_ceramico_fv_paredes_macicas": {
        "nome": "Bloco ceramico vazado com paredes macicas, furo vertical (NBR 15270-1)",
        "estrutural": True,
        "pesos": {14.0: (2.0, 2.3, 2.7)},
    },
    "bloco_ceramico_fv_paredes_vazadas": {
        "nome": "Bloco ceramico vazado com paredes vazadas, furo vertical (NBR 15270-1)",
        "estrutural": True,
        "pesos": {9.0: (1.1, 1.5, 1.9), 11.5: (1.4, 1.8, 2.2),
                  14.0: (1.7, 2.1, 2.5), 19.0: (2.3, 2.7, 3.1)},
    },
    "tijolo_ceramico_macico": {
        "nome": "Tijolo ceramico macico (NBR 15270-1)",
        "estrutural": True,
        "pesos": {9.0: (1.6, 2.0, 2.4), 11.5: (2.1, 2.5, 2.9),
                  14.0: (2.5, 2.9, 3.3), 19.0: (3.4, 3.8, 4.2)},
    },
    "bloco_silico_calcario_vazado": {
        "nome": "Bloco silico-calcario vazado (classe E, NBR 14974-1)",
        "estrutural": True,
        "pesos": {9.0: (1.1, 1.5, 1.9), 14.0: (1.5, 1.9, 2.3), 19.0: (1.9, 2.3, 2.7)},
    },
    "bloco_silico_calcario_perfurado": {
        "nome": "Bloco silico-calcario perfurado (classes E, F e G, NBR 14974-1)",
        "estrutural": True,
        "pesos": {11.5: (1.9, 2.3, 2.7), 14.0: (2.1, 2.5, 2.9), 17.5: (2.8, 3.2, 3.6)},
    },
    # --- ALVENARIA DE VEDACAO ---
    "bloco_concreto_vedacao": {
        "nome": "Bloco de concreto vazado (classe C, NBR 6136)",
        "estrutural": False,
        "pesos": {6.5: (1.0, 1.4, 1.8), 9.0: (1.1, 1.5, 1.9), 11.5: (1.3, 1.7, 2.1),
                  14.0: (1.4, 1.8, 2.2), 19.0: (1.8, 2.2, 2.6)},
    },
    "bloco_ceramico_furo_horizontal": {
        "nome": "Bloco ceramico vazado, furo horizontal (NBR 15270-1)",
        "estrutural": False,
        # 9 cm e 19 cm tem salto de 0,5 da coluna de 1 cm para a de 2 cm (a norma
        # arredonda assim); conferido no texto bruto da fonte.
        "pesos": {9.0: (0.7, 1.1, 1.6), 11.5: (0.9, 1.3, 1.7),
                  14.0: (1.1, 1.5, 1.9), 19.0: (1.4, 1.8, 2.3)},
    },
    "bloco_concreto_celular": {
        "nome": "Bloco de concreto celular autoclavado (classe C25, NBR 13438)",
        "estrutural": False,
        "pesos": {7.5: (0.5, 0.9, 1.3), 10.0: (0.6, 1.0, 1.4), 12.5: (0.8, 1.2, 1.6),
                  15.0: (0.9, 1.3, 1.7), 17.5: (1.1, 1.5, 1.9), 20.0: (1.2, 1.6, 2.0)},
    },
    "bloco_vidro": {
        "nome": "Bloco de vidro (decorativo, sem resistencia ao fogo)",
        "estrutural": False,
        "pesos": {8.0: (0.8, None, None)},     # a norma so tabela a coluna sem revestimento
    },
}

# ---------------------------------------------------------------------------
# Tabela 3 - divisorias e caixilhos (kN/m2)
# ---------------------------------------------------------------------------
DIVISORIAS = {
    "drywall": {"nome": "Drywall (montantes metalicos, 4 chapas de 12,5 mm, la de "
                        "rocha/vidro de 50 mm)", "espessura_cm": (7.0, 30.0), "peso": 0.5},
    "divisoria_retratil": {"nome": "Divisorias retrateis (exceto com vidro)",
                           "espessura_cm": (7.0, 12.0), "peso": 0.6},
    "caixilho_aluminio": {"nome": "Caixilho de aluminio com vidro simples 4 mm",
                          "espessura_cm": None, "peso": 0.2},
    "caixilho_ferro": {"nome": "Caixilho de ferro com vidro simples 4 mm",
                       "espessura_cm": None, "peso": 0.3},
    "caixilho_piso_a_piso": {"nome": "Caixilho de piso a piso, h <= 4,0 m",
                             "espessura_cm": None, "peso": 0.5},
}

# ---------------------------------------------------------------------------
# Tabela 10 - cargas variaveis de uso. 'q' em kN/m2, 'Q' concentrada em kN
# (a norma traz "-" na maioria das linhas -> None). 'redutivel' vem da nota "a"
# da propria tabela ("Reducao de cargas variaveis nao permitida") combinada com
# a lista do item 6.12.
# Cargas concentradas (6.2): salvo indicacao, atuam distribuidas em 75x75 cm, na
# posicao mais desfavoravel, e sao verificadas ISOLADAS da carga distribuida.
# ---------------------------------------------------------------------------
CARGAS_USO = {
    # edificios residenciais
    "residencial_dormitorio": {"local": "Dormitorios", "q": 1.5, "Q": None, "redutivel": True},
    "residencial_sala_copa_cozinha": {"local": "Sala, copa, cozinha", "q": 1.5,
                                      "Q": None, "redutivel": True},
    "residencial_sanitario": {"local": "Sanitarios", "q": 1.5, "Q": None, "redutivel": True},
    "residencial_servico": {"local": "Despensa, area de servico e lavanderia",
                            "q": 2.0, "Q": None, "redutivel": True},
    "residencial_corredor_privativo": {"local": "Corredores dentro de unidades autonomas",
                                       "q": 1.5, "Q": None, "redutivel": True},
    "residencial_corredor_comum": {"local": "Corredores de uso comum", "q": 3.0,
                                   "Q": None, "redutivel": True},
    "sotao": {"local": "Sotao", "q": 2.0, "Q": None, "redutivel": False,
              "nota": "nota a: reducao nao permitida"},
    "forro_manutencao": {"local": "Forros acessiveis apenas para manutencao e sem "
                                  "estoque de materiais", "q": 0.1, "Q": None,
                         "redutivel": False,
                         "nota": "notas a e r; forro inacessivel e sem estoque dispensa "
                                 "carga variavel de uso"},
    # comerciais / escritorios
    "escritorio_sala_uso_geral": {"local": "Salas de uso geral e sanitarios", "q": 2.5,
                                  "Q": None, "redutivel": True},
    "escritorio_corredor_privativo": {"local": "Corredores dentro de unidades autonomas",
                                      "q": 2.5, "Q": None, "redutivel": True},
    "escritorio_corredor_comum": {"local": "Corredores de uso comum", "q": 3.0,
                                  "Q": None, "redutivel": True},
    # escadas e passarelas (nota t: nos trechos em balanco verificar alternancia)
    "escada_residencial_privativa": {"local": "Escadas: residenciais/hoteis, dentro de "
                                              "unidades autonomas", "q": 2.5, "Q": None,
                                     "redutivel": True},
    "escada_residencial_comum": {"local": "Escadas: residenciais/hoteis, uso comum",
                                 "q": 3.0, "Q": None, "redutivel": True},
    "escada_comercial": {"local": "Escadas: edificios comerciais, clubes, escritorios, "
                                  "bibliotecas", "q": 3.0, "Q": None, "redutivel": True},
    "escada_com_acesso_publico": {"local": "Escadas: com acesso publico", "q": 3.0,
                                  "Q": None, "redutivel": True},
    "escada_sem_acesso_publico": {"local": "Escadas: sem acesso publico", "q": 2.5,
                                  "Q": None, "redutivel": True},
    "escada_escola": {"local": "Escadas: escolas", "q": 3.0, "Q": None, "redutivel": True},
    "escada_shopping": {"local": "Escadas: cinemas, centros comerciais, shopping centers",
                        "q": 4.0, "Q": None, "redutivel": True},
    "escada_arquibancada": {"local": "Escadas servindo arquibancadas", "q": 5.0,
                            "Q": None, "redutivel": False,
                            "nota": "assembleias/arquibancadas: reducao nao permitida (6.12)"},
    # sacadas, varandas e terracos (nota j: 2 kN/m na borda com guarda-corpo)
    "sacada_residencial": {"local": "Balcoes, sacadas, varandas e terracos: residencial",
                           "q": 2.5, "Q": None, "redutivel": True,
                           "nota": "nota j: prever 2 kN/m na borda, alem do p.proprio do "
                                   "guarda-corpo, e as forcas horizontais de 6.3"},
    "sacada_comercial": {"local": "Balcoes, sacadas, varandas e terracos: comercial",
                         "q": 3.0, "Q": None, "redutivel": True,
                         "nota": "nota j: prever 2 kN/m na borda"},
    "sacada_acesso_publico": {"local": "Balcoes, sacadas, varandas e terracos com acesso "
                                       "publico", "q": 4.0, "Q": None, "redutivel": True,
                              "nota": "nota j: prever 2 kN/m na borda"},
    # lojas / shopping
    "loja": {"local": "Lojas, centros comerciais: circulacoes e lojas em geral", "q": 4.0,
             "Q": None, "redutivel": False, "nota": "nota a: reducao nao permitida"},
    "loja_deposito": {"local": "Lojas: depositos", "q": 5.0, "Q": None, "redutivel": False,
                      "nota": "area de estoque: reducao nao permitida (6.12)"},
    "loja_sanitario": {"local": "Lojas: sanitarios", "q": 2.0, "Q": None, "redutivel": False},
    "loja_administrativa": {"local": "Lojas: salas administrativas", "q": 2.5, "Q": None,
                            "redutivel": False},
    "praca_alimentacao_publico": {"local": "Praca de alimentacao: area de publico", "q": 5.0,
                                  "Q": None, "redutivel": False},
    "praca_alimentacao_cozinha": {"local": "Praca de alimentacao: cozinhas e servicos",
                                  "q": 7.5, "Q": None, "redutivel": False},
    # restaurantes
    "restaurante_salao": {"local": "Restaurantes: salao", "q": 3.0, "Q": None,
                          "redutivel": False, "nota": "nota a: reducao nao permitida"},
    "restaurante_deposito": {"local": "Restaurantes: depositos", "q": 5.0, "Q": None,
                             "redutivel": False},
    # escolas
    "escola_sala_aula": {"local": "Escolas: sala de aula", "q": 3.0, "Q": None,
                         "redutivel": False, "nota": "nota a: reducao nao permitida"},
    "escola_corredor": {"local": "Escolas: corredor", "q": 3.0, "Q": None, "redutivel": False},
    "escola_sanitario": {"local": "Escolas: sanitarios, vestiarios", "q": 2.0, "Q": None,
                         "redutivel": False},
    # bibliotecas
    "biblioteca_leitura_sem_estantes": {"local": "Bibliotecas: sala de leitura sem estantes",
                                        "q": 3.0, "Q": None, "redutivel": False},
    "biblioteca_leitura_com_estantes": {"local": "Bibliotecas: sala de leitura com estantes",
                                        "q": 4.0, "Q": None, "redutivel": False},
    "biblioteca_arquivo_deslizante": {"local": "Bibliotecas: regioes de arquivos deslizantes",
                                      "q": 5.0, "Q": None, "redutivel": False},
    # coberturas
    "cobertura_manutencao": {"local": "Coberturas com acesso apenas para manutencao ou "
                                      "inspecao", "q": 1.0, "Q": None, "redutivel": False,
                             "nota": "coberturas: reducao nao permitida (6.12); verificar "
                                     "acumulo de agua (5.5); elemento isolado de cobertura "
                                     "suporta 1 kN concentrado isolado (6.4)"},
    "cobertura_placas_solares": {"local": "Coberturas com placas de aquecimento solar ou "
                                          "fotovoltaicas", "q": 1.5, "Q": None,
                                 "redutivel": False},
    # garagens (remetidas pela Tab.10 ao item 6.6.1 / Tabela 13)
    "garagem_ate_30kN": {"local": "Garagens e estacionamentos, veiculos com PBT <= 30 kN "
                                  "(categoria I, Tabela 13)", "q": 3.0, "Q": 12.0,
                         "redutivel": False,
                         "nota": "Tab.13 cat.I: Q = 12 kN em 20x20 cm, isolada da "
                                 "distribuida; forcas horizontais de impacto Fx = 100 kN e "
                                 "Fy = 50 kN aplicadas a H = 0,5 m nos pilares sujeitos a "
                                 "impacto; as cargas indicadas nao podem ser reduzidas"},
    "ginasio_esportes": {"local": "Ginasios de esportes", "q": 5.0, "Q": None,
                         "redutivel": False},
}

# carga concentrada da Tabela 13, categoria I (garagem de veiculos ate 30 kN)
GARAGEM_CAT_I = {
    "PBT_max_kN": 30.0, "q": 3.0, "altura_max_m": 2.3, "Q_k": 12.0,
    "Q_area_m": (0.20, 0.20), "Fx": 100.0, "Fy": 50.0, "H_aplicacao_m": 0.5,
    "redutivel": False,
}

# elemento isolado de cobertura (6.4): 1 kN concentrado, isolado das demais variaveis
Q_ELEMENTO_ISOLADO_COBERTURA = 1.0

# nota j da Tabela 10: borda de balcao/sacada/varanda/terraco com guarda-corpo
Q_BORDA_GUARDA_CORPO = 2.0            # kN/m, alem do peso proprio do guarda-corpo

# ---------------------------------------------------------------------------
# Tabela 11 - paredes divisorias SEM POSICAO DEFINIDA em projeto
# faixas (limite superior de p.p. em kN/m, carga adicional em kN/m2)
# ---------------------------------------------------------------------------
TAB11_FAIXAS = ((1.0, 0.5), (2.0, 0.75), (3.0, 1.0))
PP_MAX_SEM_POSICAO = 3.0              # acima disso: NAO PERMITIDO como distribuida
Q_DISPENSA_TAB11 = 4.0                # kN/m2: dispensa a carga adicional

# ---------------------------------------------------------------------------
# Tabela 12 - forcas horizontais em guarda-corpos e barreiras (kN/m), atuando a
# 1,1 m acima do piso acabado e perpendiculares ao eixo longitudinal (6.3).
# ---------------------------------------------------------------------------
H_APLICACAO_GUARDA_CORPO = 1.10       # m acima do piso acabado
F_EVENTO_EXTREMO = 5.0                # kN/m (nota b, recomendado minimo)
FD_ANCORAGEM_BALANCIM = 15.0          # kN, forca concentrada de calculo (6.3)

GUARDA_CORPO = {
    "passarela_inspecao": {"local": "Passarelas acessiveis apenas para inspecao e "
                                    "manutencao", "F": 0.4, "evento_extremo": False},
    "privativa_residencial": {"local": "Areas privativas de unidades residenciais, "
                                       "escritorios, quartos de hoteis, quartos e "
                                       "enfermarias de hospitais", "F": 1.0,
                              "evento_extremo": False},
    "cobertura_sem_acesso_publico": {"local": "Coberturas, terracos, passarelas etc. sem "
                                              "acesso publico", "F": 1.0,
                                     "evento_extremo": False},
    "escada_privativa": {"local": "Escadas privativas ou sem acesso publico, escadas de "
                                  "emergencia em edificios", "F": 1.0,
                         "evento_extremo": False},
    "escada_panoramica": {"local": "Escadas panoramicas", "F": 2.0, "evento_extremo": False},
    "acesso_publico": {"local": "Areas com acesso publico (exceto os casos seguintes)",
                       "F": 1.0, "evento_extremo": True},
    "fluxo_paralelo": {"local": "Zonas de fluxo de pessoas em areas de acesso publico, "
                                "barreiras PARALELAS a direcao do fluxo", "F": 2.0,
                       "evento_extremo": True},
    "fluxo_perpendicular": {"local": "Zonas de fluxo de pessoas em areas de acesso publico, "
                                     "barreiras PERPENDICULARES a direcao do fluxo",
                            "F": 3.0, "evento_extremo": True},
    "multidoes": {"local": "Areas de possivel acolhimento de multidoes, galerias e shopping "
                           "centers (exceto dentro das lojas), plataformas de passageiros",
                  "F": 3.0, "evento_extremo": True},
    "estoque_industrial": {"local": "Areas de estoque (incluindo livros e documentos) e "
                                    "atividades industriais", "F": 2.0,
                           "evento_extremo": False},
}

# ---------------------------------------------------------------------------
# Tabela 19 / item 6.12 - reducao de cargas variaveis
# ---------------------------------------------------------------------------
# (numero maximo de pisos da faixa, multiplicador alpha_n)
TAB19_FAIXAS = ((3, 1.0), (4, 0.8), (5, 0.6))
ALPHA_N_MIN = 0.4                     # "6 ou mais"

# item 6.12: elementos a que a reducao se aplica. Vigas e lajes NAO entram.
ELEMENTOS_COM_REDUCAO = ("pilar", "fundacao")

USOS_NAO_REDUTIVEIS_TEXTO = (
    "garagens, reservatorios, coberturas, jardins, depositos de explosivos e "
    "inflamaveis e areas de estoque em geral, areas de armamentos, areas tecnicas, "
    "instalacoes nucleares, industrias, estadios, teatros e cinemas, passarelas, "
    "assembleias com assentos fixos ou moveis e demais areas cujas cargas variaveis "
    "nao sejam redutiveis, conforme a Tabela 10"
)


# ===========================================================================
# Consultas
# ===========================================================================
def carga_uso(chave):
    """Carga variavel de uso da Tabela 10 (copia do registro). Levanta KeyError com
    a lista de chaves validas se o ambiente nao existir - NUNCA devolve um default
    generico: um 'loja' silenciosamente dimensionado como 'dormitorio' (4,0 -> 1,5
    kN/m2) e exatamente o erro que um fallback esconderia."""
    if chave not in CARGAS_USO:
        raise KeyError(
            "ambiente '%s' nao consta na Tabela 10 da NBR 6120:2019 implementada. "
            "Ambientes disponiveis: %s" % (chave, ", ".join(sorted(CARGAS_USO)))
        )
    return dict(CARGAS_USO[chave])


def peso_alvenaria(tipo, espessura_cm, revestimento_cm=1.0):
    """Peso do painel de parede em kN/m2 DE PAREDE (Tabela 2), para a espessura
    nominal do bloco e a espessura de revestimento POR FACE (0, 1 ou 2 cm).

    A tabela e DISCRETA: espessura fora das tabeladas levanta ValueError em vez de
    cair na mais proxima (arredondar 'para a de baixo' subestimaria o peso em
    silencio; arredondar 'para a de cima' e igualmente uma invencao). Idem para o
    revestimento, que a norma so tabela em 0, 1 e 2 cm."""
    if tipo not in ALVENARIAS:
        raise KeyError("alvenaria '%s' nao consta na Tabela 2. Tipos: %s"
                       % (tipo, ", ".join(sorted(ALVENARIAS))))
    reg = ALVENARIAS[tipo]
    esp = float(espessura_cm)
    if esp not in reg["pesos"]:
        raise ValueError(
            "espessura %.4g cm nao tabelada para '%s' (NBR 6120 Tab.2). "
            "Espessuras tabeladas: %s cm" % (esp, tipo,
             ", ".join("%g" % e for e in sorted(reg["pesos"]))))
    rev = float(revestimento_cm)
    if rev not in REVESTIMENTOS_CM:
        raise ValueError("revestimento de %.4g cm por face nao tabelado (a NBR 6120 "
                         "Tab.2 tabela 0, 1 e 2 cm)" % rev)
    p = reg["pesos"][esp][REVESTIMENTOS_CM.index(rev)]
    if p is None:
        raise ValueError("a Tabela 2 nao tabela '%s' com %g cm de revestimento por face"
                         % (tipo, rev))
    return p


def carga_linear_parede(tipo, espessura_cm, altura_m, revestimento_cm=1.0):
    """Carga LINEAR de parede sobre viga/laje (kN/m) = peso do painel (kN/m2 de
    parede) x altura da parede (m).

    ROTULO x GEOMETRIA: o valor da Tabela 2 e por m2 DE PAINEL DE PAREDE e ja inclui
    o revestimento das duas faces; nao e peso especifico (kN/m3) e nao deve ser
    multiplicado pela espessura do bloco. Multiplicar pela espessura daria uma carga
    ~10x menor - e o mesmo tipo de erro do 'bbox nao e eixo'."""
    if altura_m <= 0:
        raise ValueError("altura da parede deve ser > 0")
    return peso_alvenaria(tipo, espessura_cm, revestimento_cm) * float(altura_m)


def peso_divisoria(chave):
    """Peso de divisoria/caixilho da Tabela 3 (kN/m2)."""
    if chave not in DIVISORIAS:
        raise KeyError("divisoria '%s' nao consta na Tabela 3. Opcoes: %s"
                       % (chave, ", ".join(sorted(DIVISORIAS))))
    return DIVISORIAS[chave]["peso"]


def forca_guarda_corpo(chave, evento_extremo=False):
    """Forca horizontal em guarda-corpo/barreira (Tabela 12), em kN/m, a 1,1 m acima
    do piso acabado. Com evento_extremo=True aplica a nota b (minimo 5,0 kN/m) - so
    e admitida nas linhas que a norma marca com a nota b."""
    if chave not in GUARDA_CORPO:
        raise KeyError("barreira '%s' nao consta na Tabela 12. Opcoes: %s"
                       % (chave, ", ".join(sorted(GUARDA_CORPO))))
    reg = GUARDA_CORPO[chave]
    F = reg["F"]
    avisos = []
    if evento_extremo:
        if not reg["evento_extremo"]:
            raise ValueError(
                "a nota b (evento extremo) da Tabela 12 se aplica as barreiras de area "
                "de acesso publico; '%s' nao e marcada com a nota b" % chave)
        F = max(F, F_EVENTO_EXTREMO)
        avisos.append("nota b: evento extremo (superlotacao, manifestacoes, tumultos) "
                      "-> recomendado minimo 5,0 kN/m")
    return {"F_kN_m": F, "h_aplicacao_m": H_APLICACAO_GUARDA_CORPO,
            "local": reg["local"], "avisos": avisos,
            "obs": "perpendicular ao eixo longitudinal da barreira, "
                   "independentemente da altura da barreira (6.3)"}


# ===========================================================================
# Tabela 11 - paredes divisorias sem posicao definida
# ===========================================================================
def parede_sem_posicao_definida(pp_kN_m, q_pavimento_kN_m2):
    """Carga variavel ADICIONAL uniformemente distribuida por paredes divisorias sem
    posicao definida em projeto (Tabela 11 + texto de 6.2).

    pp_kN_m: peso proprio da PAREDE ACABADA, por metro linear (kN/m).
    q_pavimento_kN_m2: carga variavel de projeto do pavimento (kN/m2).

    GATE (saturacao silenciosa): acima de 3,0 kN/m a norma diz NAO PERMITIDO - a
    parede tem de entrar como carga LINEAR PERMANENTE na posicao de projeto. Uma
    implementacao que saturasse na ultima faixa (1,0 kN/m2) devolveria OK e
    subestimaria a estrutura sem nunca reprovar. Aqui ok=False.
    Dispensa: q >= 4,0 kN/m2 dispensa a adicional, EXCETO quando pp > 3,0 kN/m."""
    pp = float(pp_kN_m)
    if pp <= 0:
        raise ValueError("peso proprio da parede acabada deve ser > 0 kN/m")
    if pp > PP_MAX_SEM_POSICAO + 1e-9:
        return {
            "ok": False, "adicional_kN_m2": None, "dispensada": False,
            "motivo": "p.p. = %.2f kN/m > 3,0 kN/m: a Tabela 11 marca NAO PERMITIDO. "
                      "A carga linear deve ser considerada como PERMANENTE, segundo a "
                      "posicao de projeto (nao como carga distribuida adicional). A "
                      "dispensa por q >= 4,0 kN/m2 tambem nao se aplica neste caso."
                      % pp,
        }
    if float(q_pavimento_kN_m2) >= Q_DISPENSA_TAB11 - 1e-9:
        return {
            "ok": True, "adicional_kN_m2": 0.0, "dispensada": True,
            "motivo": "carga variavel do pavimento (%.2f kN/m2) >= 4,0 kN/m2: a "
                      "consideracao da carga adicional e dispensada (6.2)"
                      % float(q_pavimento_kN_m2),
        }
    for lim, adic in TAB11_FAIXAS:
        if pp <= lim + 1e-9:
            return {"ok": True, "adicional_kN_m2": adic, "dispensada": False,
                    "motivo": "Tabela 11, faixa p.p. <= %.1f kN/m" % lim}
    raise AssertionError("faixa da Tabela 11 nao coberta para p.p. = %.3f" % pp)


# ===========================================================================
# Tabela 19 / item 6.12 - reducao de cargas variaveis na descida de cargas
# ===========================================================================
def alpha_n(n_pisos):
    """Multiplicador alpha_n da Tabela 19 pelo numero de pisos que atuam sobre o
    elemento. 1 a 3 -> 1,0 ; 4 -> 0,8 ; 5 -> 0,6 ; 6 ou mais -> 0,4."""
    n = int(n_pisos)
    if n < 1:
        raise ValueError("numero de pisos que atuam sobre o elemento deve ser >= 1")
    for lim, a in TAB19_FAIXAS:
        if n <= lim:
            return a
    return ALPHA_N_MIN


def multiplicadores_pavimentos(pavimentos, elemento="pilar"):
    """Aplica o item 6.12 a uma pilha de pavimentos, do TOPO para a BASE.

    pavimentos: lista de dicts, do mais alto para o mais baixo, cada um com
      'nome'      : rotulo do pavimento (ex.: 'Cobertura', 'Tipo 5');
      'uso'       : chave da Tabela 10 (CARGAS_USO) OU um rotulo livre de grupo;
      'qk'        : carga variavel caracteristica (kN/m2) - opcional se 'uso' for
                    chave da Tabela 10, quando entao e lida de la;
      'redutivel' : opcional; default = o que a Tabela 10 diz para aquele uso;
      'area'      : opcional; area do pavimento em planta (m2). Grupos de mesmo uso
                    com AREAS DIFERENTES sao grupos distintos (6.12/Fig.14).
    elemento: 'pilar' ou 'fundacao'. A reducao de 6.12 se aplica APENAS a esses; para
      'viga' ou 'laje' devolve alpha = 1,0 em tudo, com o motivo declarado.

    Mecanica adotada (6.12, Figuras 12 a 14): cada pavimento recebe o SEU proprio
    multiplicador conforme a posicao dele na contagem descendente do grupo de pisos
    adjacentes de mesmo uso, e a carga acumulada e a soma dos qk ja multiplicados
    piso a piso. Pavimento inteiramente ocupado por carga variavel NAO REDUTIVEL
    recebe alpha = 1,0 e NAO interrompe a sequencia do grupo (a contagem e pausada e
    retomada de onde parou).

    Retorna lista, na mesma ordem, com {'nome','uso','qk','redutivel','alpha',
    'n_grupo','qk_reduzido','acumulado_kN_m2','motivo'}."""
    if elemento not in ELEMENTOS_COM_REDUCAO:
        motivo_bloqueio = (
            "o item 6.12 permite a reducao apenas na determinacao de esforcos "
            "solicitantes em PILARES E FUNDACOES; para '%s' nao ha reducao" % elemento)
    else:
        motivo_bloqueio = None

    saida = []
    grupo_ref = None
    n = 0
    acumulado = 0.0
    for pav in pavimentos:
        uso = pav.get("uso")
        if uso in CARGAS_USO:
            reg = CARGAS_USO[uso]
            qk = float(pav["qk"]) if pav.get("qk") is not None else reg["q"]
            padrao_redutivel = reg["redutivel"]
        elif pav.get("qk") is not None:
            qk = float(pav["qk"])
            padrao_redutivel = True
        else:
            raise KeyError(
                "pavimento '%s': informe 'qk' ou use uma chave da Tabela 10 em 'uso' "
                "(recebido: %r)" % (pav.get("nome", "?"), uso))
        redutivel = bool(pav.get("redutivel", padrao_redutivel))

        if motivo_bloqueio is not None:
            alpha, n_grupo, motivo = 1.0, None, motivo_bloqueio
        elif not redutivel:
            # 1,0 x qk e a sequencia do grupo NAO e interrompida (6.12)
            alpha, n_grupo = 1.0, None
            motivo = ("carga variavel nao redutivel (6.12): alpha = 1,0; nao interrompe "
                      "a sequencia dos multiplicadores do grupo")
        else:
            area = pav.get("area")
            chave_grupo = (uso, round(float(area), 3) if area else None)
            if chave_grupo != grupo_ref:
                if grupo_ref is not None and grupo_ref[0] == chave_grupo[0]:
                    motivo_grupo = ("novo grupo: mesmo uso, area em planta diferente "
                                    "(6.12/Fig.14) -> contagem reiniciada")
                else:
                    motivo_grupo = "inicio do grupo de pisos adjacentes de mesmo uso"
                grupo_ref = chave_grupo
                n = 0
            else:
                motivo_grupo = "mesmo grupo"
            n += 1
            alpha = alpha_n(n)
            n_grupo = n
            motivo = "%s; %do piso do grupo -> alpha_n = %.1f (Tab.19)" % (
                motivo_grupo, n, alpha)

        qk_red = qk * alpha
        acumulado += qk_red
        saida.append({
            "nome": pav.get("nome", uso), "uso": uso, "qk": qk, "redutivel": redutivel,
            "alpha": alpha, "n_grupo": n_grupo, "qk_reduzido": round(qk_red, 4),
            "acumulado_kN_m2": round(acumulado, 4), "motivo": motivo,
        })
    return saida


def registro_reducoes(linhas):
    """Texto do registro das reducoes adotadas, exigido pelo item 6.12 ("As reducoes
    adotadas devem ser registradas nos documentos do projeto"). Sai no memorial e no
    executivo, nao so no calculo."""
    L = ["REDUCAO DE CARGAS VARIAVEIS - ABNT NBR 6120:2019, item 6.12 e Tabela 19",
         "Registro exigido pelo item 6.12 (as reducoes adotadas devem ser registradas "
         "nos documentos do projeto).",
         "",
         "%-22s %-28s %8s %7s %8s %12s" % ("PAVIMENTO", "USO", "qk", "alpha", "qk*alpha",
                                           "ACUMULADO")]
    L.append("-" * 92)
    for r in linhas:
        L.append("%-22s %-28s %8.2f %7.2f %8.2f %12.2f" % (
            str(r["nome"])[:22], str(r["uso"])[:28], r["qk"], r["alpha"],
            r["qk_reduzido"], r["acumulado_kN_m2"]))
    L.append("-" * 92)
    nao_red = [r["nome"] for r in linhas if not r["redutivel"]]
    if nao_red:
        L.append("Pavimentos com carga variavel NAO REDUTIVEL (alpha = 1,0): %s"
                 % ", ".join(str(x) for x in nao_red))
        L.append("Usos em que a reducao nao e permitida (6.12): %s"
                 % USOS_NAO_REDUTIVEIS_TEXTO)
    L.append("A reducao NAO se aplica a vigas nem a lajes (6.12: pilares e fundacoes).")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Autoconferencia da Tabela 2 (rotulo x geometria) - usada pelos testes
# ---------------------------------------------------------------------------
def _coerencia_tab2():
    """Confere cada linha da Tabela 2 contra a NOTA da propria tabela (revestimento a
    19 kN/m3 -> 1 cm por face soma 0,38 kN/m2). Serve de guarda contra erro de
    transcricao: se alguem reeditar a tabela e trocar um digito, o desvio aparece aqui.

    A conferencia NAO pode partir do valor tabelado sem revestimento como se fosse
    exato: as tres colunas sao arredondamentos a 1 decimal de um mesmo peso-base b
    (o painel sem revestimento), e comparar 2,3 com 2,0 + 0,38 = 2,38 acusaria falso
    positivo em linhas perfeitamente coerentes (b = 1,96 -> 1,96/2,34/2,72 -> 2,0/2,3/
    2,7). O teste correto e de CONSISTENCIA: existe algum b real que, arredondado,
    reproduza as tres colunas ao mesmo tempo? Isso equivale a intersectar os
    intervalos de b admitidos por cada coluna.

    Devolve a lista das linhas para as quais essa intersecao e VAZIA - ou seja, nenhum
    peso-base explica as tres colunas. As duas unicas divergencias conhecidas (bloco
    ceramico de furo horizontal, 9 e 19 cm) sao arredondamento da propria norma,
    CONFERIDAS no texto bruto da fonte, e estao em DIVERGENCIAS_TAB2_CONHECIDAS."""
    inc = 2.0 * 0.01 * 19.0                     # 0,38 kN/m2 por cm de revestimento/face
    meio = 0.05 + 1e-9                          # meia casa do arredondamento a 1 decimal
    fora = []
    for tipo, reg in ALVENARIAS.items():
        for esp, pesos in reg["pesos"].items():
            lo, hi = -1e9, 1e9
            for i, rev in enumerate(REVESTIMENTOS_CM):
                if pesos[i] is None:
                    continue
                # coluna i admite b em [p_i - inc*rev - meio ; p_i - inc*rev + meio)
                lo = max(lo, pesos[i] - inc * rev - meio)
                hi = min(hi, pesos[i] - inc * rev + meio)
            if lo >= hi:
                fora.append((tipo, esp, pesos, round(lo, 3), round(hi, 3)))
    return fora


DIVERGENCIAS_TAB2_CONHECIDAS = (
    ("bloco_ceramico_furo_horizontal", 9.0, 2.0),
    ("bloco_ceramico_furo_horizontal", 19.0, 2.0),
)
