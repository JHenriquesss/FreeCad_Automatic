# ============================================================================
# laje_concreto.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona LAJE MACICA de concreto armado (ABNT NBR 6118:2014) apoiada sobre
# vigas - o elemento que faltava para o framework projetar qualquer edificacao
# que nao seja galpao terreo. Cobre:
#   - espessura minima e gamma_n de balanco (13.2.4.1 / Tabela 13.2);
#   - esforcos por TEORIA DAS PLACAS (tabelas de Bares, adaptadas para nu=0,20),
#     lajes armadas em DUAS direcoes, 9 casos de vinculacao; e por VIGA de faixa
#     unitaria quando lambda = ly/lx > 2 (armada em UMA direcao);
#   - compatibilizacao dos momentos negativos entre lajes contiguas;
#   - armadura de flexao (17.2.2, bloco retangular) REUSANDO fundacao_sapata
#     ._armadura_flexao e rho_min (ja aferidas contra Alonso/Araujo/Carvalho);
#   - armaduras minimas de laje (19.3.3 / Tabela 19.1) e detalhamento (20.1:
#     phi <= h/8 ; s <= min(2h ; 20 cm) principal ; 33 cm secundaria);
#   - cortante SEM armadura transversal (19.4.1, V_Rd1 - formulacao de LAJE, que
#     e diferente do modelo de trelica da viga);
#   - ELS de deformacao: flecha elastica (tabela de Bares) + fissuracao (Branson)
#     + fluencia (17.3.2.1.2, alpha_f = dxi/(1+50 rho')), limites da Tabela 13.3;
#   - ELS-W de fissuracao, REUSANDO fissuracao_nbr6118;
#   - ancoragem REUSANDO fundacao_sapata.comprimento_ancoragem (9.4);
#   - reacoes nas vigas de apoio por quinhoes de carga (14.7.6.1);
#   - laje NERVURADA (13.2.4.2): mesa, nervura e criterio de dispensa.
# AFERICAO: exemplo resolvido de Carvalho & Figueiredo Filho, "Calculo e
# Detalhamento de Estruturas Usuais de Concreto Armado segundo a NBR 6118:2014",
# 4a ed., EdUFSCar, 2014, Cap.7 (Exemplo 1, p.358-368) - lajes L1/L2/L3.
# As tabelas de Bares foram TRANSCRITAS da fonte (Quadros 7.2 a 7.5) e conferidas
# uma a uma contra uma solucao INDEPENDENTE de placa de Kirchhoff por diferencas
# finitas (tests/test_laje_tabela_bares.py) - transcricao de tabela por OCR e
# candidata classica a cristalizar erro (episodio "AR300").
# Unidades: m, kN ; fck/fyk em kN/m2 ; momentos em kN.m/m ; As em m2/m.
# ============================================================================
"""Laje macica de concreto armado (NBR 6118:2014): esforcos por teoria das placas
(tabelas de Bares), armadura de flexao e minimos de laje, cortante 19.4.1, ELS de
flecha (Tab 13.3) e de fissuracao, reacoes nas vigas e laje nervurada."""

from __future__ import annotations

import math
import re

import fissuracao_nbr6118 as fis
import fundacao_sapata as fs

GAMMA_C_CONC = 25.0        # peso especifico do concreto armado (kN/m3), NBR 6120
GF = 1.4                   # ponderacao das acoes (ELU normal)
ES_ACO = 210e6             # modulo do aco (kN/m2)
LAM_MIN, LAM_MAX = 1.00, 2.00     # faixa das tabelas de Bares (lambda = ly/lx)

# ---------------------------------------------------------------------------
# Tabela 13.2 (13.2.4.1) - espessura MINIMA de laje macica.
# ---------------------------------------------------------------------------
H_MIN_TAB = {
    "cobertura": 0.07,           # cobertura nao em balanco
    "piso": 0.08,                # piso nao em balanco
    "balanco": 0.10,             # laje em balanco
    "veiculo_ate_30kN": 0.10,    # lajes com veiculos de peso total <= 30 kN
    "veiculo_acima_30kN": 0.12,  # lajes com veiculos de peso total > 30 kN
    "lisa": 0.16,                # laje lisa (apoiada diretamente em pilares)
    "cogumelo": 0.14,            # laje-cogumelo, fora do capitel
}
H_BALANCO_GAMMA_N = 0.19    # balanco com h < 19 cm -> majorar esforcos (Tab 13.2)

# ---------------------------------------------------------------------------
# Tabela 13.3 - deslocamentos limites (l = MENOR vao do painel de laje).
# 'divisorias_leves' tem ainda o teto absoluto de 25 mm; 'alvenaria' o de 10 mm.
# ---------------------------------------------------------------------------
LIM_FLECHA = {
    "visual": (250.0, None),          # aceitabilidade sensorial (visivel)
    "vibracao": (350.0, None),        # vibracoes sentidas no piso (so acidental)
    "drenagem": (250.0, None),        # superficies que devem drenar agua
    "piso_plano": (350.0, None),      # pavimentos que devem permanecer planos
    "piso_plano_pos": (600.0, None),  # ... apos a construcao do piso
    "divisorias_leves": (250.0, 0.025),
    "alvenaria": (500.0, 0.010),      # paredes de alvenaria sobre a laje
}
THETA_APOIO_LIM = 0.0017          # rotacao limite no apoio (rad), Tab 13.3

# ---------------------------------------------------------------------------
# TABELAS DE BARES (Carvalho & Figueiredo, Quadros 7.3/7.4/7.5; nu = 0,20).
# Casos de vinculacao (Figura 7.5). x e SEMPRE a direcao do MENOR vao lx:
#   1 - 4 bordas apoiadas
#   2 - 1 borda menor engastada (engaste perpendicular a y)
#   3 - 1 borda maior engastada (engaste perpendicular a x)
#   4 - 2 bordas adjacentes engastadas
#   5 - 2 bordas menores engastadas (perpendiculares a y)
#   6 - 2 bordas maiores engastadas (perpendiculares a x)
#   7 - 3 bordas engastadas (a apoiada e uma borda MENOR)
#   8 - 3 bordas engastadas (a apoiada e uma borda MAIOR)
#   9 - 4 bordas engastadas
# Valor tabelado: (mu_x, mu_x', mu_y, mu_y'), com mu' = 0 onde nao ha engaste
# naquela direcao. Momento = mu * p * lx^2 / 100 (expressoes 7.18 a 7.21).
# Conferencia independente: tests/test_laje_tabela_bares.py (placa de Kirchhoff
# por diferencas finitas). Celulas corrigidas por corrupcao de OCR estao
# marcadas com [OCR] e o valor lido no arquivo-fonte.
# ---------------------------------------------------------------------------
_LAMBDAS = tuple(round(1.00 + 0.05 * i, 2) for i in range(21))

MU_BARES = {
    1: ((4.41, 0, 4.41, 0), (4.80, 0, 4.45, 0), (5.18, 0, 4.49, 0),
        (5.56, 0, 4.49, 0), (5.90, 0, 4.48, 0), (6.27, 0, 4.45, 0),
        (6.60, 0, 4.42, 0), (6.93, 0, 4.37, 0), (7.25, 0, 4.33, 0),
        (7.55, 0, 4.30, 0), (7.86, 0, 4.25, 0), (8.12, 0, 4.20, 0),
        (8.34, 0, 4.14, 0),   # [OCR] lido "3,14"; serie 4,20 -> 4,07 e a placa
        (8.62, 0, 4.07, 0), (8.86, 0, 4.00, 0), (9.06, 0, 3.96, 0),
        (9.27, 0, 3.91, 0), (9.45, 0, 3.83, 0), (9.63, 0, 3.75, 0),
        (9.77, 0, 3.71, 0), (10.00, 0, 3.64, 0)),
    2: ((3.07, 0, 3.94, 8.52), (3.42, 0, 3.78, 8.79), (3.77, 0, 3.90, 9.18),
        (4.14, 0, 3.97, 9.53), (4.51, 0, 4.05, 9.88), (4.88, 0, 4.10, 10.16),
        (5.25, 0, 4.15, 10.41), (5.60, 0, 4.18, 10.64), (5.95, 0, 4.21, 10.86),
        (6.27, 0, 4.19, 11.05), (6.60, 0, 4.18, 11.23), (6.90, 0, 4.17, 11.39),
        (7.21, 0, 4.14, 11.55),
        (7.50, 0, 4.12, 11.67),   # [OCR] lido "7,42"
        (7.79, 0, 4.09, 11.79),   # [OCR] lido "7,62"
        (8.06, 0, 4.05, 11.88),   # [OCR] lido "7,66"
        (8.31, 0, 3.99, 11.96),   # [OCR] lido "7,69"
        (8.55, 0, 3.97, 12.03),   # [OCR] lido "8,22"
        (8.74, 0, 3.94, 12.14), (8.97, 0, 3.88, 12.17),
        (9.18, 0, 3.80, 12.20)),
    3: ((3.94, 8.52, 3.07, 0), (4.19, 8.91, 2.84, 0), (4.43, 9.30, 2.76, 0),
        (4.64, 9.63, 2.68, 0), (4.85, 9.95, 2.59, 0), (5.03, 10.22, 2.51, 0),
        (5.20, 10.48, 2.42, 0), (5.36, 10.71, 2.34, 0), (5.51, 10.92, 2.25, 0),
        (5.64, 11.10, 2.19, 0), (5.77, 11.27, 2.12, 0), (5.87, 11.42, 2.04, 0),
        (5.98, 11.55, 1.95, 0), (6.07, 11.67, 1.87, 0), (6.16, 11.80, 1.79, 0),
        (6.24, 11.92, 1.74, 0), (6.31, 12.04, 1.68, 0), (6.38, 12.14, 1.64, 0),
        (6.43, 12.24, 1.59, 0), (6.47, 12.29, 1.54, 0), (6.51, 12.34, 1.48, 0)),
    4: ((2.81, 6.99, 2.81, 6.99), (3.05, 7.43, 2.81, 7.18),
        (3.30, 7.87, 2.81, 7.36), (3.53, 8.28, 2.80, 7.50),
        (3.76, 8.69, 2.79, 7.63), (3.96, 9.03, 2.74, 7.72),
        (4.16, 9.37, 2.69, 7.81), (4.33, 9.65, 2.65, 7.88),
        (4.51, 9.93, 2.60, 7.94),
        (4.66, 10.41, 2.53, 8.00),   # [OCR] mu_y ilegivel; serie 2,60 -> 2,47
        (4.81, 10.62, 2.47, 8.06), (4.93, 10.82, 2.39, 8.09),
        (5.06, 10.99, 2.31, 8.12), (5.16, 11.16, 2.24, 8.14),
        (5.27, 11.30, 2.16, 8.15), (5.36, 11.43, 2.11, 8.16),
        (5.45, 11.55, 2.04, 8.17), (5.53, 11.57, 1.99, 8.17),
        (5.60, 11.67, 1.93, 8.18), (5.67, 11.78, 1.91, 8.19),
        (5.74, 11.89, 1.88, 8.20)),
    5: ((2.15, 0, 3.17, 6.99), (2.47, 0, 3.32, 7.43), (2.78, 0, 3.47, 7.87),
        (3.08, 0, 3.58, 8.26), (3.38, 0, 3.70, 8.65), (3.79, 0, 3.80, 9.03),
        (4.15, 0, 3.90, 9.33), (4.50, 0, 3.96, 9.69), (4.85, 0, 4.03, 10.00),
        (5.19, 0, 4.09, 10.25), (5.53, 0, 4.14, 10.49), (5.86, 0, 4.16, 10.70),
        (6.18, 0, 4.17, 10.91), (6.48, 0, 4.14, 11.08), (6.81, 0, 4.12, 11.24),
        (7.11, 0, 4.12, 11.39),
        (7.41, 0, 4.10, 11.52),   # [OCR] lido "11,43" (quebra a serie 11,39 -> 11,65)
        (7.68, 0, 4.08, 11.65), (7.95, 0, 4.04, 11.77), (8.21, 0, 3.99, 11.83),
        (8.47, 0, 3.92, 11.88)),
    6: ((3.17, 6.99, 2.15, 0), (3.29, 7.20, 2.07, 0), (3.42, 7.41, 1.99, 0),
        (3.52, 7.56, 1.89, 0), (3.63, 7.70, 1.80, 0), (3.71, 7.82, 1.74, 0),
        (3.79, 7.93, 1.67, 0), (3.84, 8.02, 1.59, 0), (3.90, 8.11, 1.52, 0),
        (3.94, 8.13, 1.45, 0), (3.99, 8.15, 1.38, 0), (4.03, 8.20, 1.34, 0),
        (4.06, 8.25, 1.28, 0), (4.09, 8.28, 1.23, 0), (4.12, 8.30, 1.18, 0),
        (4.14, 8.31, 1.15, 0), (4.15, 8.32, 1.11, 0), (4.16, 8.33, 1.08, 0),
        (4.17, 8.33, 1.04, 0), (4.17, 8.33, 1.01, 0), (4.18, 8.33, 0.97, 0)),
    7: ((2.13, 5.46, 2.60, 6.17), (2.38, 5.98, 2.66, 6.46),
        (2.63, 6.50, 2.71, 6.75), (2.87, 7.11, 2.75, 6.97),
        (3.11, 7.72, 2.78, 7.19),
        (3.34, 8.16, 2.79, 7.36),   # [OCR] lidos "3,43" e "8,81" (fora da serie)
        (3.56, 8.59, 2.77, 7.51), (3.76, 8.74, 2.74, 7.63),
        (3.96, 8.88, 2.71, 7.74), (4.15, 9.16, 2.67, 7.83),
        (4.32, 9.44, 2.63, 7.91), (4.48, 9.68, 2.60, 7.98),
        (4.63, 9.91, 2.55, 8.02), (4.78, 10.13, 2.50, 8.03),
        (4.92, 10.34, 2.45, 8.10), (5.04, 10.53, 2.39, 8.13),
        (5.17, 10.71, 2.32, 8.17), (5.26, 10.88, 2.27, 8.16),
        (5.36, 11.04, 2.22, 8.14), (5.45, 11.20, 2.14, 8.13),
        (5.55, 11.35, 2.07, 8.12)),
    8: ((2.60, 6.17, 2.13, 5.46), (2.78, 6.47, 2.09, 5.56),
        (2.95, 6.76, 2.04, 5.65), (3.09, 6.99, 1.98, 5.70),
        (3.23, 7.22, 1.92, 5.75), (3.34, 7.40, 1.85, 5.75),
        (3.46, 7.57, 1.78, 5.76), (3.55, 7.70, 1.72, 5.75),
        (3.64, 7.82, 1.64, 5.74), (3.71, 7.91, 1.59, 5.73),
        (3.78, 8.00, 1.53, 5.72), (3.84, 8.07, 1.47, 5.69),
        (3.89, 8.14, 1.42, 5.66), (3.94, 8.20, 1.37, 5.62),
        (3.98, 8.25, 1.32, 5.58), (4.01, 8.30, 1.27, 5.56),
        (4.04, 8.34, 1.20, 5.54), (4.07, 8.38, 1.17, 5.55),
        (4.10, 8.42, 1.14, 5.56), (4.11, 8.45, 1.11, 5.60),
        (4.13, 8.47, 1.08, 5.64)),
    9: ((2.11, 5.15, 2.11, 5.15), (2.31, 5.50, 2.10, 5.29),
        (2.50, 5.85, 2.09, 5.43), (2.73, 6.14, 2.06, 5.51),
        (2.94, 6.43, 2.02, 5.59), (3.04, 6.67, 1.97, 5.64),
        (3.13, 6.90, 1.91, 5.68), (3.25, 7.09, 1.86, 5.69),
        (3.38, 7.28, 1.81, 5.70), (3.48, 7.43, 1.73, 5.71),
        (3.58, 7.57, 1.66, 5.72), (3.66, 7.68, 1.60, 5.72),
        (3.73, 7.79, 1.54, 5.72), (3.80, 7.88, 1.47, 5.72),
        (3.86, 7.97, 1.40, 5.72), (3.91, 8.05, 1.36, 5.72),
        (3.95, 8.12, 1.32, 5.72), (3.98, 8.18, 1.26, 5.72),
        (4.01, 8.24, 1.21, 5.72), (4.04, 8.29, 1.19, 5.72),
        (4.07, 8.33, 1.16, 5.72)),
}

# Quadro 7.2 - coeficiente alpha da flecha ELASTICA: f = alpha*p*lx^4/(100*E*h^3).
ALPHA_FLECHA = {
    1: (4.67, 5.17, 5.64, 6.09, 6.52, 6.95, 7.36, 7.76, 8.14, 8.51, 8.87,
        9.22, 9.54, 9.86, 10.15, 10.43, 10.71, 10.96, 11.21, 11.44, 11.68),
    2: (3.20, 3.61, 4.04, 4.47, 4.91, 5.34, 5.77, 6.21, 6.62, 7.02, 7.41,
        7.81, 8.17, 8.52, 8.87, 9.19, 9.52, 9.82, 10.11, 10.39, 10.68),
    3: (3.20, 3.42, 3.63, 3.82, 4.02, 4.18, 4.35, 4.50, 4.65, 4.78, 4.92,
        5.00, 5.09, 5.13, 5.17, 5.26, 5.36, 5.43, 5.50, 5.58, 5.66),
    4: (2.42, 2.67, 2.91, 3.12, 3.34, 3.55, 3.73, 3.92, 4.08, 4.23, 4.38,
        4.53, 4.65, 4.77, 4.88, 4.97, 5.07, 5.15, 5.23, 5.31, 5.39),
    5: (2.21, 2.55, 2.92, 3.29, 3.67, 4.07, 4.48, 4.92, 5.31, 5.73, 6.14,
        6.54, 6.93, 7.33, 7.70, 8.06, 8.43, 8.77, 9.08, 9.41, 9.72),
    6: (2.21, 2.31, 2.41, 2.48, 2.56, 2.63, 2.69, 2.72, 2.75, 2.80, 2.84,
        2.86, 2.87, 2.87, 2.88, 2.88, 2.89, 2.89, 2.90, 2.90, 2.91),
    7: (1.81, 2.04, 2.27, 2.49, 2.72, 2.95, 3.16, 3.36, 3.56, 3.73, 3.91,
        4.07, 4.22, 4.37, 4.51, 4.63, 4.75, 4.87, 4.98, 5.08, 5.19),
    # [OCR] caso 8: lidos "2,53" (1,55), "2,87" (1,60) e "2,78" (1,65), que
    # quebram a serie monotona 2,68 -> 2,79; substituidos pela interpolacao.
    8: (1.81, 1.92, 2.04, 2.14, 2.24, 2.33, 2.42, 2.48, 2.56, 2.62, 2.68,
        2.71, 2.74, 2.77, 2.79, 2.81, 2.83, 2.85, 2.87, 2.89, 2.91),
    9: (1.46, 1.60, 1.74, 1.87, 1.98, 2.10, 2.20, 2.30, 2.37, 2.45, 2.51,
        2.57, 2.63, 2.68, 2.72, 2.76, 2.80, 2.83, 2.85, 2.88, 2.91),
}

# Bordas engastadas de cada caso: 'x0'/'x1' sao as bordas perpendiculares a x
# (de comprimento ly) e 'y0'/'y1' as perpendiculares a y (de comprimento lx).
ENGASTES = {1: (), 2: ("y0",), 3: ("x0",), 4: ("x0", "y0"), 5: ("y0", "y1"),
            6: ("x0", "x1"), 7: ("x0", "y0", "y1"), 8: ("x0", "x1", "y0"),
            9: ("x0", "x1", "y0", "y1")}

# Coeficientes de momento de faixa unitaria (laje armada em UMA direcao):
# (coeficiente do momento positivo, coeficiente do momento negativo no engaste).
COEF_1D = {"apoiada": (1.0 / 8.0, 0.0),
           "engastada_apoiada": (9.0 / 128.0, 1.0 / 8.0),
           "biengastada": (1.0 / 24.0, 1.0 / 12.0),
           "balanco": (0.0, 1.0 / 2.0)}

BITOLAS_LAJE = (5.0, 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0)   # mm
S_COMERCIAL = tuple(round(0.025 * i, 4) for i in range(3, 15))  # 7,5 a 35 cm
S_MIN_LAJE = 0.075                                              # espacamento minimo pratico
K_ENGASTE = math.sqrt(3.0)   # tg(60 graus): charneira a partir do apoio engastado (14.7.6.1)


def _pt(txt):
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", txt)


def _area_barra(phi_mm):
    return math.pi * (phi_mm / 1000.0) ** 2 / 4.0


# ---------------------------------------------------------------------------
# 1. GEOMETRIA E MINIMOS (13.2.4.1 / Tabela 13.2)
# ---------------------------------------------------------------------------

def h_minima(tipo="piso"):
    """Espessura minima de laje macica (Tabela 13.2). tipo em H_MIN_TAB."""
    if tipo not in H_MIN_TAB:
        raise ValueError("tipo de laje desconhecido: %r (use %s)"
                         % (tipo, sorted(H_MIN_TAB)))
    return H_MIN_TAB[tipo]


def gamma_n_balanco(h):
    """Majorador de esforcos de laje EM BALANCO com h < 19 cm (Tabela 13.2, com a
    mesma expressao da Tabela 13.1 de pilar): gamma_n = 1,95 - 0,05*h[cm] >= 1."""
    if h >= H_BALANCO_GAMMA_N:
        return 1.0
    return max(1.95 - 0.05 * (h * 100.0), 1.0)


# ---------------------------------------------------------------------------
# 2. ESFORCOS
# ---------------------------------------------------------------------------

def _interp(serie, lam):
    """Interpola linearmente uma serie tabelada em lambda (passo 0,05)."""
    if lam <= _LAMBDAS[0]:
        return serie[0]
    if lam >= _LAMBDAS[-1]:
        return serie[-1]
    i = min(int((lam - _LAMBDAS[0]) / 0.05), len(_LAMBDAS) - 2)
    l0, l1 = _LAMBDAS[i], _LAMBDAS[i + 1]
    t = (lam - l0) / (l1 - l0)
    a, b = serie[i], serie[i + 1]
    if isinstance(a, tuple):
        return tuple(x + (y - x) * t for x, y in zip(a, b))
    return a + (b - a) * t


def coeficientes_bares(caso, lam):
    """(mu_x, mu_x', mu_y, mu_y') do caso de vinculacao para lambda = ly/lx.
    SATURACAO: a tabela termina em lambda = 2,00. Acima disso a laje e armada em
    UMA direcao (14.7.6.2) - devolver o valor de 2,00 SUBESTIMA o momento; por
    isso a funcao devolve tambem o flag 'saturou', que o orquestrador transforma
    em reprovacao (nunca em OK=True calado)."""
    if caso not in MU_BARES:
        raise ValueError("caso de vinculacao invalido: %r (1 a 9)" % (caso,))
    if lam < LAM_MIN - 1e-9:
        raise ValueError("lambda = ly/lx = %.3f < 1: troque lx por ly (lx e o MENOR vao)"
                         % lam)
    saturou = lam > LAM_MAX + 1e-9
    mu = _interp(MU_BARES[caso], lam)
    return {"mu_x": mu[0], "mu_x_neg": mu[1], "mu_y": mu[2], "mu_y_neg": mu[3],
            "lambda": lam, "saturou": saturou}


def momentos_bares(caso, lx, ly, p):
    """Momentos maximos de placa (kN.m/m) pelas expressoes 7.18 a 7.21:
    m = mu * p * lx^2 / 100, com lx = MENOR vao."""
    if lx <= 0 or ly <= 0:
        raise ValueError("vaos da laje devem ser positivos (lx=%r, ly=%r)" % (lx, ly))
    if ly < lx:
        lx, ly = ly, lx
    c = coeficientes_bares(caso, ly / lx)
    base = p * lx ** 2 / 100.0
    return {"m_x": c["mu_x"] * base, "m_y": c["mu_y"] * base,
            "x_x": c["mu_x_neg"] * base, "x_y": c["mu_y_neg"] * base,
            "lambda": c["lambda"], "saturou": c["saturou"],
            "mu": (c["mu_x"], c["mu_x_neg"], c["mu_y"], c["mu_y_neg"]),
            "lx": lx, "ly": ly, "p": p}


def momentos_uma_direcao(vinculacao, l, p):
    """Momentos de faixa unitaria (laje armada em UMA direcao), kN.m/m."""
    if vinculacao not in COEF_1D:
        raise ValueError("vinculacao invalida: %r (use %s)"
                         % (vinculacao, sorted(COEF_1D)))
    cm, cx = COEF_1D[vinculacao]
    return {"m_x": cm * p * l ** 2, "x_x": cx * p * l ** 2, "m_y": 0.0, "x_y": 0.0,
            "vinculacao": vinculacao, "l": l, "p": p, "saturou": False}


def compatibiliza_momentos_negativos(x1, x2, criterio="norma"):
    """Momento negativo na face comum a duas lajes contiguas.
    'norma' : o MAIOR entre a media dos dois e 80% do maior (pratica corrente);
    'maior' : o maior dos dois (a favor da seguranca; e o que Carvalho &
              Figueiredo adotam no exemplo do Cap.7).
    Devolve tambem o acrescimo de momento POSITIVO de cada laje quando o negativo
    adotado fica abaixo do da laje isolada."""
    a, b = abs(x1), abs(x2)
    if criterio == "maior":
        x = max(a, b)
    elif criterio == "norma":
        x = max((a + b) / 2.0, 0.80 * max(a, b))
    else:
        raise ValueError("criterio invalido: %r ('norma' ou 'maior')" % (criterio,))
    return {"X": x, "d_m1": max(a - x, 0.0) / 2.0, "d_m2": max(b - x, 0.0) / 2.0,
            "criterio": criterio}


# ---------------------------------------------------------------------------
# 3. ARMADURAS (17.2.2 + 19.3.3/Tabela 19.1 + 20.1)
# ---------------------------------------------------------------------------

FATOR_AS_MIN = {"negativa": 1.0, "negativa_borda": 0.67, "positiva_1d": 1.0,
                "positiva_2d": 0.67, "secundaria": 0.5}


def armadura_minima(fck, h, papel):
    """As,min de LAJE por metro de largura (m2/m) - Tabela 19.1 / 19.3.3.2.
    papel: 'negativa' | 'negativa_borda' | 'positiva_1d' | 'positiva_2d' |
    'secundaria' (esta ainda sujeita aos minimos de 20% da principal e
    0,9 cm2/m, aplicados em armadura_secundaria)."""
    if papel not in FATOR_AS_MIN:
        raise ValueError("papel de armadura invalido: %r (use %s)"
                         % (papel, sorted(FATOR_AS_MIN)))
    return FATOR_AS_MIN[papel] * fs.rho_min(fck / 1000.0) * h * 1.0


def armadura_secundaria(As_principal, fck, h):
    """Armadura de distribuicao de laje armada em UMA direcao (Tabela 19.1):
    As/s >= 20% da principal, >= 0,9 cm2/m e rho_s >= 0,5*rho_min."""
    return max(0.20 * As_principal, 0.9e-4, armadura_minima(fck, h, "secundaria"))


def detalha_malha(As_req, h, principal=True, phi_max_mm=None):
    """Escolhe (bitola, espacamento) de uma malha de laje para As_req (m2/m).
    Regras de 20.1: phi <= h/8 ; s <= min(2h ; 20 cm) na armadura principal da
    regiao de maiores momentos ; s <= 33 cm na secundaria. Prefere a MENOR bitola
    que atenda (mais barras -> fissuracao melhor), com espacamento comercial
    (multiplo de 2,5 cm) arredondado PARA BAIXO. 'saturou' avisa que nem a maior
    bitola no menor espacamento cobre As_req - nesse caso a laje esta fina demais
    e o resultado NAO pode ser dado como atendido."""
    s_max = min(2.0 * h, 0.20) if principal else 0.33
    phi_lim = (h / 8.0) * 1000.0
    if phi_max_mm is not None:
        phi_lim = min(phi_lim, phi_max_mm)
    base = {"s_max": s_max, "phi_lim_mm": phi_lim}
    if As_req <= 0:
        return dict(base, phi_mm=0.0, s=s_max, As_ef=0.0, saturou=False)
    melhor = None
    for phi in BITOLAS_LAJE:
        if phi > phi_lim + 1e-9:
            continue
        A1 = _area_barra(phi)
        s_teorico = A1 / As_req
        cand = [s for s in S_COMERCIAL
                if s <= min(s_teorico, s_max) + 1e-12 and s >= S_MIN_LAJE - 1e-12]
        if not cand:
            continue
        s = max(cand)
        # entre as bitolas que servem, a de MENOR desperdicio de aco; empate ->
        # a menor bitola (mais barras, fissuracao melhor).
        chave = (round(A1 / s, 9), phi)
        if melhor is None or chave < melhor[0]:
            melhor = (chave, dict(base, phi_mm=phi, s=s, As_ef=A1 / s, saturou=False))
    if melhor:
        return melhor[1]
    phi = max([p for p in BITOLAS_LAJE if p <= phi_lim + 1e-9] or [BITOLAS_LAJE[0]])
    return dict(base, phi_mm=phi, s=S_MIN_LAJE,
                As_ef=_area_barra(phi) / S_MIN_LAJE, saturou=True)


def dimensiona_seccao(M_d, b, d, h, fck, fyk, papel, phi_max_mm=None):
    """Armadura de uma faixa de laje sob M_d (kN.m/m): flexao (17.2.2, reusando
    fundacao_sapata._armadura_flexao), minimo de laje e malha detalhada."""
    As, x_d, z, ok_dom = fs._armadura_flexao(M_d, b, d, fck, fyk)
    secao_ok = As is not None
    As = As or 0.0
    As_min = armadura_minima(fck, h, papel)
    As_ad = max(As, As_min)
    As_max = 0.04 * b * h                       # 17.3.5.2.4 (As+As' <= 4% Ac)
    malha = detalha_malha(As_ad, h, principal=(papel != "secundaria"),
                          phi_max_mm=phi_max_mm)
    return {"M_d": M_d, "As": As, "As_min": As_min, "As_adotada": As_ad,
            "As_max": As_max, "x_d": x_d, "z": z, "ok_dominio": ok_dom,
            "secao_ok": secao_ok, "governa_minimo": As_min > As,
            "ok_As_max": As_ad <= As_max + 1e-12, "malha": malha, "papel": papel}


def ancoragem_laje(phi_mm, fck, fyk=500e3, gancho=True):
    """Ancoragem das barras da laje (9.4) - reusa a rotina ja aferida da sapata."""
    return fs.comprimento_ancoragem(phi_mm, fck_MPa=fck / 1000.0,
                                    fyk_MPa=fyk / 1000.0, gancho=gancho)


# ---------------------------------------------------------------------------
# 4. CORTANTE EM LAJE SEM ARMADURA TRANSVERSAL (19.4.1)
# ---------------------------------------------------------------------------

def cortante_laje(V_sd, bw, d, fck, As1, sigma_cp=0.0, metade_no_apoio=False):
    """V_Rd1 = [tau_Rd*k*(1,2+40*rho1) + 0,15*sigma_cp]*bw*d  (19.4.1), com
    tau_Rd = 0,25*fctd ; k = 1,0 se 50% da armadura inferior NAO chega ao apoio,
    senao k = |1,6 - d| >= 1 (d em m) ; rho1 = As1/(bw*d) <= 0,02.
    Verifica tambem a biela: V_Rd2 = 0,5*alpha_v1*fcd*bw*0,9d.
    Formulacao de LAJE - diferente do modelo de trelica da viga."""
    fck_MPa = fck / 1000.0
    if fck_MPa <= 50.0:
        fctm_MPa = 0.3 * fck_MPa ** (2.0 / 3.0)       # 8.2.5 ate C50
    else:
        fctm_MPa = 2.12 * math.log(1.0 + 0.11 * fck_MPa)  # 8.2.5 C55-C90 (G49)
    fctd = 0.7 * fctm_MPa / 1.4 * 1000.0     # kN/m2
    tau_rd = 0.25 * fctd
    k = 1.0 if metade_no_apoio else max(abs(1.6 - d), 1.0)
    rho1 = min(As1 / (bw * d), 0.02) if bw * d > 0 else 0.0
    V_rd1 = (tau_rd * k * (1.2 + 40.0 * rho1) + 0.15 * sigma_cp) * bw * d
    fcd = fck / 1.4
    alpha_v1 = 1.0 - fck_MPa / 250.0
    V_rd2 = 0.5 * alpha_v1 * fcd * bw * 0.9 * d
    return {"V_sd": V_sd, "V_rd1": V_rd1, "V_rd2": V_rd2, "k": k, "rho1": rho1,
            "tau_rd": tau_rd, "u_cort": V_sd / V_rd1 if V_rd1 > 0 else float("inf"),
            "u_biela": V_sd / V_rd2 if V_rd2 > 0 else float("inf"),
            "ok": V_sd <= V_rd1 + 1e-9 and V_sd <= V_rd2 + 1e-9,
            "exige_armadura": V_sd > V_rd1 + 1e-9}


# ---------------------------------------------------------------------------
# 5. ELS - FLECHA (17.3.2 + Tabela 13.3)
# ---------------------------------------------------------------------------

def xi_fluencia(t_meses):
    """Funcao xi(t) da fluencia (17.3.2.1.2): xi = 0,68*0,996^t*t^0,32 para
    t <= 70 meses ; xi = 2 para t >= 70 meses (t em meses)."""
    if t_meses >= 70.0:
        return 2.0
    if t_meses <= 0:
        return 0.0
    return 0.68 * (0.996 ** t_meses) * t_meses ** 0.32


def alpha_f(t_meses=70.0, t0_meses=0.47, rho_linha=0.0):
    """Fator da flecha diferida (17.3.2.1.2): alpha_f = dxi/(1+50*rho').
    Default t0 = 0,47 mes (14 dias, retirada do escoramento)."""
    d_xi = xi_fluencia(t_meses) - xi_fluencia(t0_meses)
    return max(d_xi, 0.0) / (1.0 + 50.0 * rho_linha)


def flecha_laje(caso, lx, ly, p_servico, h, fck, As_tracao=0.0, M_servico=None,
                considerar_fissuracao=True, t_meses=70.0, t0_meses=0.47,
                rho_linha=0.0, d=None):
    """Flecha de laje: elastica pela tabela de Bares
    (f = alpha*p*lx^4/(100*E_cs*h^3), eq. 7.16) x correcao de fissuracao
    (Ic/I_eq, Branson 17.3.2) x (1 + alpha_f).
    Com considerar_fissuracao=False fica a flecha ELASTICA de secao bruta, que e
    a permitida por 14.6.4.1 e a usada no exemplo do livro."""
    if ly < lx:
        lx, ly = ly, lx
    lam = ly / lx
    alpha = _interp(ALPHA_FLECHA[caso], lam)
    E_cs = fis.modulo_secante(fck)
    f_el = alpha * p_servico * lx ** 4 / (100.0 * E_cs * h ** 3)
    I_c = h ** 3 / 12.0                               # por metro de largura
    fator_fis, I_eq, M_r = 1.0, I_c, None
    if considerar_fissuracao and As_tracao > 0 and M_servico:
        dd = d if d else 0.8 * h
        M_r = 1.5 * fis.fctm(fck) * I_c / (h / 2.0)   # 17.3.1 (secao retangular)
        ae = ES_ACO / E_cs
        disc = (ae * As_tracao) ** 2 + 2.0 * ae * As_tracao * dd
        x = -ae * As_tracao + math.sqrt(disc)         # b = 1,0 m
        I_II = x ** 3 / 3.0 + ae * As_tracao * (dd - x) ** 2
        if abs(M_servico) > M_r:
            r = (M_r / abs(M_servico)) ** 3
            I_eq = min(r * I_c + (1.0 - r) * I_II, I_c)
        fator_fis = I_c / I_eq
    af = alpha_f(t_meses, t0_meses, rho_linha)
    f_im = f_el * fator_fis
    return {"alpha": alpha, "lambda": lam, "E_cs": E_cs, "f_elastica": f_el,
            "f_imediata": f_im, "f_total": f_im * (1.0 + af), "alpha_f": af,
            "fator_fissuracao": fator_fis, "I_c": I_c, "I_eq": I_eq, "M_r": M_r,
            "fissurou": bool(M_r and M_servico and abs(M_servico) > M_r)}


def limite_flecha(tipo, l):
    """Limite de deslocamento da Tabela 13.3. l = MENOR vao do painel."""
    if tipo not in LIM_FLECHA:
        raise ValueError("limite de flecha desconhecido: %r (use %s)"
                         % (tipo, sorted(LIM_FLECHA)))
    div, teto = LIM_FLECHA[tipo]
    lim = l / div
    return min(lim, teto) if teto else lim


# ---------------------------------------------------------------------------
# 6. REACOES NAS VIGAS DE APOIO (14.7.6.1 - quinhoes de carga)
# ---------------------------------------------------------------------------

def reacoes_apoios(caso, lx, ly, p, n=2000):
    """Reacao media por metro em cada borda (kN/m) pelos quinhoes de carga da
    14.7.6.1: as charneiras saem dos vertices por retas inclinadas de 45 graus
    entre dois apoios do MESMO tipo e de 60 graus a partir do apoio ENGASTADO
    quando o outro e simplesmente apoiado. Isso equivale a atribuir cada ponto a
    borda que minimiza dist/k, com k = tg(60) = raiz(3) na borda engastada e
    k = tg(45) = 1 na apoiada. As areas sao integradas em faixas (a fronteira e
    poligonal), de modo que a SOMA das reacoes fecha a carga total do painel.
    Aferido contra os Quadros 7.8/7.9 de Carvalho & Figueiredo (q = k*p*lx/10):
    laje quadrada com uma borda menor engastada -> k 1,83 / 1,83 / 4,02 / 2,32."""
    if ly < lx:
        lx, ly = ly, lx
    eng = set(ENGASTES[caso])
    k = {b: (K_ENGASTE if b in eng else 1.0) for b in ("x0", "x1", "y0", "y1")}
    A = {b: 0.0 for b in k}
    ty_tot = ly * k["y0"] / (k["y0"] + k["y1"])          # limite do quinhao em y
    ty1_tot = ly - ty_tot
    dx = lx / n
    for i in range(n):
        x = (i + 0.5) * dx
        a0, a1 = x / k["x0"], (lx - x) / k["x1"]
        m = min(a0, a1)
        bx = "x0" if a0 <= a1 else "x1"
        t0 = min(k["y0"] * m, ty_tot)
        t1 = min(k["y1"] * m, ty1_tot)
        A["y0"] += t0 * dx
        A["y1"] += t1 * dx
        A[bx] += max(ly - t0 - t1, 0.0) * dx
    out = {}
    for b in ("x0", "x1", "y0", "y1"):
        comp = ly if b in ("x0", "x1") else lx
        out[b] = {"area": A[b], "v": p * A[b] / comp if comp > 0 else 0.0,
                  "k": 10.0 * A[b] / (comp * lx) if comp * lx > 0 else 0.0,
                  "engastada": b in eng}
    return out


# ---------------------------------------------------------------------------
# 7. LAJE NERVURADA (13.2.4.2)
# ---------------------------------------------------------------------------

def verifica_nervurada(cfg):
    """Requisitos geometricos da laje nervurada (13.2.4.2).
    cfg: {'hf' mesa (m), 'bw' nervura (m), 'l0' distancia entre faces das
    nervuras (m), 'e_nerv' distancia entre EIXOS de nervuras (m),
    'phi_tubo_mm' (0 se nao ha tubulacao embutida), 'cruzamento' (bool),
    'armadura_compressao' (bool)}."""
    hf = cfg["hf"]; bw = cfg["bw"]; l0 = cfg["l0"]
    e = cfg.get("e_nerv", l0 + bw)
    phi_t = cfg.get("phi_tubo_mm", 0.0)
    avisos = []
    hf_min = max(0.04, l0 / 15.0)
    if phi_t > 0:
        hf_min = max(hf_min, 0.05 if phi_t <= 10.0 else
                     0.04 + (2.0 if cfg.get("cruzamento") else 1.0) * phi_t / 1000.0)
    ok_hf = hf >= hf_min - 1e-9
    ok_bw = bw >= 0.05 - 1e-9
    ok_arm = not (cfg.get("armadura_compressao") and bw < 0.08 - 1e-9)
    if not ok_arm:
        avisos.append("nervura com bw < 8 cm NAO pode ter armadura de compressao (13.2.4.2)")
    if e <= 0.65 + 1e-9:
        regime = "dispensa flexao da mesa; cisalhamento verificado como LAJE (19.4.1)"
    elif e <= 1.10 + 1e-9:
        como_laje = bw >= 0.12 and e <= 0.90 + 1e-9
        regime = ("exige flexao da mesa; cisalhamento como VIGA"
                  + (" (admitido como laje: e <= 90 cm e bw > 12 cm)" if como_laje else ""))
    else:
        regime = "e > 110 cm: a mesa deve ser projetada como LAJE MACICA"
        avisos.append("espacamento entre eixos de nervuras > 110 cm (13.2.4.2)")
    if not ok_hf:
        avisos.append("mesa hf = %.3f m < hf_min = %.3f m (13.2.4.2)" % (hf, hf_min))
    if not ok_bw:
        avisos.append("nervura bw = %.3f m < 5 cm (13.2.4.2)" % bw)
    return {"hf": hf, "hf_min": hf_min, "bw": bw, "e_nerv": e, "regime": regime,
            "ok_hf": ok_hf, "ok_bw": ok_bw, "ok_armadura_compressao": ok_arm,
            "avisos": avisos, "OK": ok_hf and ok_bw and ok_arm and e <= 1.10 + 1e-9}


# ---------------------------------------------------------------------------
# 8. ORQUESTRADOR
# ---------------------------------------------------------------------------

def _vinculacao_1d(caso):
    """Vinculacao da faixa unitaria (direcao do menor vao) equivalente ao caso."""
    n = len([b for b in ENGASTES[caso] if b in ("x0", "x1")])
    return {0: "apoiada", 1: "engastada_apoiada", 2: "biengastada"}[n]


def verifica_laje(cfg):
    """Dimensiona/verifica uma laje macica retangular apoiada em vigas.
    cfg: {
      'lx','ly'  : vaos teoricos (m); lx e trocado por ly se vier maior.
      'h'        : espessura (m). 'cobrimento' (m, default 0,025 - CAA II).
      'fck','fyk': (kN/m2). 'phi_mm': bitola preferencial (limitada a h/8).
      'caso'     : 1 a 9 (vinculacao, Figura 7.5 / tabelas de Bares).
      'g'        : permanente ALEM do peso proprio (kN/m2). 'q': acidental (kN/m2).
      'tipo'     : piso|cobertura|balanco|... (Tabela 13.2 e gamma_n).
      'psi1','psi2' : coeficientes das combinacoes frequente e quase permanente.
      'lim_flecha'  : chave da Tabela 13.3 (default 'visual' = l/250).
      'fracao_laje' : fracao do limite atribuida a laje quando a viga de apoio
                      tambem deforma (o livro usa 2/3). Default 1,0.
      'forcar_bares': mantem a tabela de placa mesmo com lambda > 2 (so para
                      estudo - o orquestrador REPROVA, ver gate de saturacao).
      'CAA'      : classe de agressividade para o ELS-W (default II).
      'considerar_fissuracao' : Branson na flecha (default True).
    }"""
    lx, ly = float(cfg["lx"]), float(cfg["ly"])
    if ly < lx:
        lx, ly = ly, lx
    h = float(cfg["h"])
    fck = cfg["fck"]; fyk = cfg["fyk"]
    cob = cfg.get("cobrimento", 0.025)
    tipo = cfg.get("tipo", "piso")
    caso = int(cfg.get("caso", 1))
    phi_pref = cfg.get("phi_mm")
    g_extra = cfg.get("g", 0.0); q = cfg.get("q", 0.0)
    psi1 = cfg.get("psi1", 0.4); psi2 = cfg.get("psi2", 0.4)
    avisos = []

    # --- geometria minima (Tabela 13.2) ------------------------------------
    h_min = h_minima(tipo)
    ok_h = h >= h_min - 1e-9
    if not ok_h:
        avisos.append("h = %.3f m < h_min = %.3f m para laje %s (Tabela 13.2)"
                      % (h, h_min, tipo))
    gn = gamma_n_balanco(h) if tipo == "balanco" else 1.0
    if gn > 1.0:
        avisos.append("balanco com h < 19 cm: esforcos majorados por gamma_n = %.2f"
                      " (Tabela 13.2)" % gn)

    # --- cargas ------------------------------------------------------------
    g = GAMMA_C_CONC * h + g_extra
    p_k = g + q
    p_d = GF * gn * p_k
    p_qp = g + psi2 * q                      # combinacao quase permanente
    p_freq = g + psi1 * q                    # combinacao frequente (ELS-W)

    # --- esforcos ----------------------------------------------------------
    lam = ly / lx
    duas_direcoes = lam <= LAM_MAX + 1e-9 or bool(cfg.get("forcar_bares"))
    if duas_direcoes:
        M = momentos_bares(caso, lx, ly, p_d)
    else:
        vinc = _vinculacao_1d(caso)
        M = momentos_uma_direcao(vinc, lx, p_d)
        M["lambda"] = lam
        avisos.append("lambda = %.2f > 2: laje armada em UMA direcao (14.7.6.2),"
                      " faixa unitaria %s" % (lam, vinc))
    saturou_tabela = bool(M.get("saturou"))
    if saturou_tabela:
        avisos.append("SATURACAO: lambda = %.2f fora da tabela de placa (que termina"
                      " em 2,00) - o momento sai SUBESTIMADO; use laje armada em uma"
                      " direcao" % lam)

    # --- armaduras ---------------------------------------------------------
    phi_est = (phi_pref or 10.0) / 1000.0
    d = h - cob - phi_est / 2.0
    if d <= 0:
        raise ValueError("altura util nao positiva: h=%.3f cob=%.3f" % (h, cob))
    papel_pos = "positiva_2d" if duas_direcoes else "positiva_1d"
    arm = {}
    arm["m_x"] = dimensiona_seccao(M["m_x"], 1.0, d, h, fck, fyk, papel_pos, phi_pref)
    if duas_direcoes:
        arm["m_y"] = dimensiona_seccao(M["m_y"], 1.0, d, h, fck, fyk, papel_pos,
                                       phi_pref)
    else:
        As_sec = armadura_secundaria(arm["m_x"]["As_adotada"], fck, h)
        arm["m_y"] = {"M_d": 0.0, "As": 0.0, "As_min": As_sec, "As_adotada": As_sec,
                      "As_max": 0.04 * h, "x_d": 0.0, "z": d, "ok_dominio": True,
                      "secao_ok": True, "governa_minimo": True, "ok_As_max": True,
                      "papel": "secundaria",
                      "malha": detalha_malha(As_sec, h, principal=False,
                                             phi_max_mm=phi_pref)}
    for chave in ("x_x", "x_y"):
        if M.get(chave, 0.0) > 0:
            arm[chave] = dimensiona_seccao(M[chave], 1.0, d, h, fck, fyk,
                                           "negativa", phi_pref)

    # --- cortante (19.4.1) na borda mais carregada -------------------------
    reac = reacoes_apoios(caso, lx, ly, p_k) if duas_direcoes else None
    v_k = max(r["v"] for r in reac.values()) if reac else p_k * lx / 2.0
    V_sd = GF * gn * v_k
    cort = cortante_laje(V_sd, 1.0, d, fck, arm["m_x"]["As_adotada"])
    if cort["exige_armadura"]:
        avisos.append("V_Sd = %.1f kN/m > V_Rd1 = %.1f kN/m: a laje exigiria armadura"
                      " transversal (19.4.2) - fora do escopo deste modulo"
                      % (V_sd, cort["V_rd1"]))

    # --- ELS: flecha (Tabela 13.3) ----------------------------------------
    # momento de servico da combinacao quase permanente para o Branson: o livro
    # recomenda usar o MAIOR momento (negativo, se existir) - 17.3.2.1.
    M_max_d = max(abs(M["m_x"]), abs(M.get("x_x", 0.0)), abs(M.get("x_y", 0.0)))
    M_qp = M_max_d / (GF * gn) * (p_qp / p_k if p_k else 1.0)
    As_ref = arm["m_x"]["As_adotada"]
    fl = flecha_laje(caso, lx, ly, p_qp, h, fck, As_tracao=As_ref, M_servico=M_qp,
                     considerar_fissuracao=cfg.get("considerar_fissuracao", True),
                     t0_meses=cfg.get("t0_meses", 0.47), d=d)
    fl_ac = flecha_laje(caso, lx, ly, q, h, fck, considerar_fissuracao=False)
    frac = cfg.get("fracao_laje", 1.0)
    lim_total = limite_flecha(cfg.get("lim_flecha", "visual"), lx) * frac
    lim_vibr = limite_flecha("vibracao", lx) * frac
    ok_flecha = fl["f_total"] <= lim_total + 1e-12
    ok_vibr = fl_ac["f_elastica"] <= lim_vibr + 1e-12
    if not ok_flecha:
        avisos.append("flecha total %.1f mm > limite %.1f mm (Tabela 13-3)"
                      % (fl["f_total"] * 1000, lim_total * 1000))
    if not ok_vibr:
        avisos.append("flecha da carga acidental %.1f mm > l/350 = %.1f mm"
                      " (vibracao, Tabela 13.3)"
                      % (fl_ac["f_elastica"] * 1000, lim_vibr * 1000))

    # --- ELS-W: fissuracao (combinacao frequente) --------------------------
    M_freq = abs(M["m_x"]) / (GF * gn) * (p_freq / p_k if p_k else 1.0)
    fissura = None
    if arm["m_x"]["As_adotada"] > 0 and M_freq > 0:
        fissura = fis.verifica_fissuracao(
            {"Ms": M_freq, "b": 1.0, "h": h, "d": d,
             "As": arm["m_x"]["As_adotada"], "fck": fck,
             "phi_mm": arm["m_x"]["malha"]["phi_mm"] or 6.3,
             "CAA": cfg.get("CAA", "II")})

    # --- ancoragem ---------------------------------------------------------
    phis = sorted({a["malha"]["phi_mm"] for a in arm.values() if a["malha"]["phi_mm"]})
    anc = {p: ancoragem_laje(p, fck, fyk) for p in phis}

    # --- gates -------------------------------------------------------------
    saturou_malha = any(a["malha"]["saturou"] for a in arm.values())
    if saturou_malha:
        avisos.append("SATURACAO: nem a maior bitola no menor espacamento cobre o As"
                      " exigido - aumente h (o detalhamento NAO pode ser dado como"
                      " atendido)")
    ok_dominio = all(a["ok_dominio"] for a in arm.values())
    ok_secao = all(a["secao_ok"] for a in arm.values())
    ok_as_max = all(a["ok_As_max"] for a in arm.values())
    if not ok_dominio:
        avisos.append("x/d acima do limite de ductilidade (14.6.4.3): a laje esta fina")
    if not ok_secao:
        avisos.append("secao insuficiente a flexao (17.2.2): aumente h ou fck")
    OK = bool(ok_h and ok_secao and ok_dominio and ok_as_max and cort["ok"]
              and ok_flecha and ok_vibr and not saturou_tabela and not saturou_malha
              and (fissura is None or fissura["OK"]))
    return {"lx": lx, "ly": ly, "lambda": lam, "h": h, "d": d, "caso": caso,
            "tipo": tipo, "duas_direcoes": duas_direcoes, "gamma_n": gn,
            "fck": fck, "fyk": fyk, "cobrimento": cob,
            "g": g, "q": q, "p_k": p_k, "p_d": p_d, "p_qp": p_qp, "p_freq": p_freq,
            "momentos": M, "armaduras": arm, "reacoes": reac, "cortante": cort,
            "flecha": fl, "flecha_acidental": fl_ac, "lim_flecha": lim_total,
            "lim_vibracao": lim_vibr, "fissuracao": fissura, "ancoragem": anc,
            "h_min": h_min, "ok_h": ok_h, "ok_flecha": ok_flecha,
            "ok_vibracao": ok_vibr, "saturou_tabela": saturou_tabela,
            "saturou_malha": saturou_malha, "avisos": avisos, "OK": OK}


def dimensiona_laje(cfg, espessuras=(0.08, 0.09, 0.10, 0.12, 0.14, 0.16, 0.18,
                                     0.20, 0.22, 0.25)):
    """Adota a MENOR espessura da lista (a partir da pedida) que atende ELU + ELS.
    Se NENHUMA atende, devolve a ultima tentada com OK=False e aviso explicito -
    nunca um OK=True por saturacao da lista."""
    h0 = cfg.get("h", 0.0)
    tentativas = [e for e in espessuras if e >= h0 - 1e-9] or [h0 or espessuras[-1]]
    r = None
    for h in tentativas:
        r = verifica_laje(dict(cfg, h=h))
        if r["OK"]:
            return r
    if r is not None:
        r["avisos"].append("SATURACAO: nenhuma espessura da lista (ate %.2f m) atende"
                           % tentativas[-1])
    return r


def relatorio_pt(r):
    """Relatorio textual da laje (numeros com virgula decimal)."""
    L = ["LAJE MACICA DE CONCRETO ARMADO (NBR 6118:2014)",
         "  Painel %.2f x %.2f m (lambda %.2f) ; h %.0f cm (h_min %.0f cm, %s)"
         " ; d %.1f cm"
         % (r["lx"], r["ly"], r["lambda"], r["h"] * 100, r["h_min"] * 100,
            r["tipo"], r["d"] * 100),
         "  Caso %d ; %s ; g %.2f + q %.2f = %.2f kN/m2 (p_d %.2f)"
         % (r["caso"], "armada em 2 direcoes" if r["duas_direcoes"]
            else "armada em 1 direcao", r["g"], r["q"], r["p_k"], r["p_d"])]
    M = r["momentos"]
    L.append("  Momentos (kN.m/m): m_x %.2f ; m_y %.2f ; X_x %.2f ; X_y %.2f"
             % (M["m_x"], M.get("m_y", 0.0), M.get("x_x", 0.0), M.get("x_y", 0.0)))
    for k in ("m_x", "m_y", "x_x", "x_y"):
        a = r["armaduras"].get(k)
        if not a:
            continue
        m = a["malha"]
        L.append("    %-4s As %.2f cm2/m%s -> phi %.1f c/ %.1f cm (%.2f cm2/m)"
                 % (k, a["As_adotada"] * 1e4,
                    " (minimo governa)" if a["governa_minimo"] else "",
                    m["phi_mm"], m["s"] * 100, m["As_ef"] * 1e4))
    c = r["cortante"]
    L.append("  Cortante 19.4.1: V_Sd %.1f <= V_Rd1 %.1f kN/m (u %.2f) -> %s"
             % (c["V_sd"], c["V_rd1"], c["u_cort"],
                "ATENDE" if c["ok"] else "REPROVA"))
    f = r["flecha"]
    L.append("  Flecha (ELS-DEF): elastica %.1f mm ; imediata %.1f ; total %.1f mm"
             " (alpha_f %.2f) <= %.1f mm -> %s"
             % (f["f_elastica"] * 1000, f["f_imediata"] * 1000, f["f_total"] * 1000,
                f["alpha_f"], r["lim_flecha"] * 1000,
                "ATENDE" if r["ok_flecha"] else "REPROVA"))
    if r["fissuracao"]:
        w = r["fissuracao"]
        L.append("  Fissuracao ELS-W: wk %.3f <= %.1f mm (CAA %s) -> %s"
                 % (w["wk_mm"], w["wk_lim_mm"], w["CAA"],
                    "ATENDE" if w["OK"] else "REPROVA"))
    if r["reacoes"]:
        L.append("  Reacoes nas vigas (kN/m): " + " ; ".join(
            "%s %.1f%s" % (b, v["v"], "*" if v["engastada"] else "")
            for b, v in sorted(r["reacoes"].items()))
            + "   (* borda engastada)")
    for a in r["avisos"]:
        L.append("  [AVISO] " + a)
    L.append("  RESULTADO: " + ("ATENDE" if r["OK"] else "NAO ATENDE"))
    return _pt("\n".join(L))


# ---------------------------------------------------------------------------
# 9. DETALHAMENTO: QUADRO DE FERROS
# ---------------------------------------------------------------------------
# Comprimentos pelo criterio do exemplo do Cap.7 (item g7 do livro):
#   - barra POSITIVA: l - 2c + 2g (o exemplo usa c = 6 cm de afastamento da
#     borda e g = 7 cm de gancho: 600 - 2*6 + 2*7 = 602 cm);
#   - barra NEGATIVA: estende-se 0,25*lx para dentro de CADA laje (lx = menor vao
#     da laje), mais o comprimento de ancoragem reto (Figura 7.18).
COB_LATERAL_BARRA = 0.06     # afastamento da barra em relacao a borda (m)
GANCHO_BARRA = 0.07          # gancho de extremidade (m)
FRACAO_NEGATIVA = 0.25       # 0,25*lx para dentro de cada laje (Figura 7.18)
PESO_KG_M_MM2 = 0.00617      # peso do aco: 0,00617 * phi[mm]^2 kg/m


def comprimento_positivo(l, cob_lateral=COB_LATERAL_BARRA, gancho=GANCHO_BARRA):
    """Comprimento de corte da barra positiva: l - 2c + 2g."""
    return l - 2.0 * cob_lateral + 2.0 * gancho


def comprimento_negativo(lx_esq, lx_dir, phi_mm, fck, fyk=500e3,
                         fracao=FRACAO_NEGATIVA):
    """Comprimento da barra negativa sobre a viga de continuidade: 0,25*lx para
    dentro de cada laje (lx = MENOR vao da laje correspondente) mais a ancoragem
    reta em cada ponta (9.4, reusando fundacao_sapata)."""
    lb = ancoragem_laje(phi_mm, fck, fyk, gancho=False)["lb_nec_mm"] / 1000.0
    return fracao * (lx_esq + lx_dir) + 2.0 * lb


def quadro_de_ferros(r, cob_lateral=COB_LATERAL_BARRA, gancho=GANCHO_BARRA):
    """Quadro de ferros da laje a partir do dict de verifica_laje: posicao,
    bitola, espacamento, comprimento unitario, quantidade e peso.
    Convencao das posicoes: N1/N2 armaduras POSITIVAS (direcoes x e y), N3/N4
    armaduras NEGATIVAS (sobre as bordas engastadas perpendiculares a x e a y).
    A quantidade sai da largura util dividida pelo espacamento (+1 barra)."""
    lx, ly, h = r["lx"], r["ly"], r["h"]
    fck, fyk = r.get("fck", 20e3), r.get("fyk", 500e3)
    eng = ENGASTES[r["caso"]] if r["duas_direcoes"] else ()
    linhas = []

    def linha(pos, chave, comprimento, largura_distribuicao, direcao, n_bordas=1):
        """n_bordas: quantas bordas engastadas recebem ESTE conjunto de barras.
        Uma laje com as DUAS bordas de uma direcao engastadas (casos 5, 6, 7, 8 e
        9) tem dois apoios distintos e portanto DOIS conjuntos de barras
        negativas - contar um so subestima o aco pela metade (achado ao comparar
        o desenho, que mostra as duas faixas, com o quadro, que contava uma)."""
        a = r["armaduras"].get(chave)
        if not a or not a["malha"]["phi_mm"]:
            return
        s = a["malha"]["s"]
        n = (int(math.floor(max(largura_distribuicao - 2 * cob_lateral, 0.0) / s))
             + 1) * n_bordas
        phi = a["malha"]["phi_mm"]
        total = n * comprimento
        linhas.append({"pos": pos, "phi_mm": phi, "s_cm": s * 100.0,
                       "direcao": direcao, "comprimento_m": comprimento, "n": n,
                       "n_bordas": n_bordas, "total_m": total,
                       "peso_kg": total * PESO_KG_M_MM2 * phi ** 2})

    linha("N1", "m_x", comprimento_positivo(lx, cob_lateral, gancho), ly, "x")
    linha("N2", "m_y", comprimento_positivo(ly, cob_lateral, gancho), lx, "y")
    n_x = len([b for b in eng if b in ("x0", "x1")])
    n_y = len([b for b in eng if b in ("y0", "y1")])
    if n_x and "x_x" in r["armaduras"]:
        phi = r["armaduras"]["x_x"]["malha"]["phi_mm"]
        linha("N3", "x_x", comprimento_negativo(lx, lx, phi, fck, fyk), ly, "x", n_x)
    if n_y and "x_y" in r["armaduras"]:
        phi = r["armaduras"]["x_y"]["malha"]["phi_mm"]
        linha("N4", "x_y", comprimento_negativo(lx, lx, phi, fck, fyk), lx, "y", n_y)
    return linhas


def peso_total_aco(quadro):
    """Peso de aco da laje (kg) - entra no orcamento e no quadro da prancha."""
    return sum(x["peso_kg"] for x in quadro)


def _selftest():
    """Amostra ponta a ponta: a laje L1 do exemplo do Cap.7 de Carvalho &
    Figueiredo (6,00 x 6,00, caso 4, C20, h = 12 cm, g = 3,56 e q = 2,0)."""
    M = momentos_bares(4, 6.0, 6.0, 5.56)
    assert abs(M["m_x"] - 5.62) < 0.02 and abs(M["x_x"] - 14.00) < 0.02, M
    r = verifica_laje({"lx": 6.0, "ly": 6.0, "h": 0.12, "fck": 20e3, "fyk": 500e3,
                       "caso": 4, "g": 0.56, "q": 2.0, "phi_mm": 8.0})
    assert r["OK"], r["avisos"]
    # a tabela de placa termina em lambda 2: acima disso NAO pode sair OK calado
    fora = verifica_laje({"lx": 2.0, "ly": 8.0, "h": 0.12, "fck": 20e3,
                          "fyk": 500e3, "caso": 1, "g": 1.0, "q": 2.0,
                          "forcar_bares": True})
    assert fora["saturou_tabela"] and not fora["OK"]
    print("laje_concreto self-test PASSED")
    print(relatorio_pt(r))


if __name__ == "__main__":
    _selftest()
