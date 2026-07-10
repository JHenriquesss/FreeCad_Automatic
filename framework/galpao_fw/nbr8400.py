# ============================================================================
# nbr8400.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Classificacao e coeficientes da ABNT NBR 8400-1:2019 (Equipamentos de elevacao
# e movimentacao de carga - Parte 1: Classificacao e cargas). Fornece, a partir da
# CLASSE da ponte (dado do fabricante/projeto), dois numeros que hoje eram input
# "A CONFIRMAR" na ponte_rolante:
#   - coef_dinamico(classe_hc, Vh): COEFICIENTE DINAMICO Psi (= impacto phi) para o
#     movimento vertical de elevacao. Psi = Psi_min + beta2*Vh (secao 6.2.2.1,
#     Figura 4). beta2 e Psi_min por classe de elevacao HC1..HC4 = Tabela 12. Vh =
#     velocidade de elevacao (m/s), limitada a 1,5 m/s (acima nao aumenta Psi).
#   - n_ciclos(classe_b): NUMERO DE CICLOS DE TENSAO da classe de utilizacao do
#     COMPONENTE estrutural B0..B10 = Tabela 9 (secao 6.1.4.2). Alimenta o N da
#     verificacao de fadiga (NBR 8800 Anexo K). Representativo = LIMITE SUPERIOR do
#     intervalo (conservador: mais ciclos -> faixa admissivel menor).
# TODOS os valores foram LIDOS do PDF (pesquisa/pdfcoffee.com_abnt-nbr-8400-1...),
# verbatim das Tabelas 9 e 12 - nao de memoria. A CLASSE (HC/B) e a velocidade Vh
# sao DADOS DO PROJETO (Ask, Do Not Invent); este modulo so traduz classe->numero.
# Unidades: Vh em m/s ; Psi adimensional ; n em ciclos. Saidas em portugues.
# ============================================================================
"""NBR 8400-1:2019: coeficiente dinamico Psi (Tab.12) e n de ciclos (Tab.9) a
partir da classe da ponte. Tabelas lidas do PDF, verbatim. Ask, Do Not Invent."""

from __future__ import annotations

# --- Tabela 12 - beta2 e Psi_min por classe de elevacao HC (verbatim PDF p.20) --
# Psi = Psi_min + beta2 * Vh   (secao 6.2.2.1 / Figura 4)
_TAB12 = {
    "HC1": (0.17, 1.05),
    "HC2": (0.34, 1.10),
    "HC3": (0.51, 1.15),
    "HC4": (0.68, 1.20),
}
VH_MAX = 1.5        # m/s - valor maximo aplicavel de Vh (p.21): acima, Psi nao sobe

# --- Tabela 9 - classes de utilizacao do COMPONENTE B0..B10 (verbatim PDF p.23) -
# (numero n de ciclos de tensao). Limite SUPERIOR de cada faixa (B10 = aberto).
_TAB9_SUP = {
    "B0": 16_000, "B1": 32_000, "B2": 63_000, "B3": 125_000, "B4": 250_000,
    "B5": 500_000, "B6": 1_000_000, "B7": 2_000_000, "B8": 4_000_000,
    "B9": 8_000_000, "B10": 8_000_000,     # B10: n >= 8e6 (aberto) -> piso 8e6
}


def coef_dinamico(classe_hc, Vh):
    """Coeficiente dinamico Psi (= impacto phi) do movimento vertical de elevacao.
    NBR 8400-1:2019 secao 6.2.2.1 / Figura 4: Psi = Psi_min + beta2*Vh, com beta2
    e Psi_min da Tabela 12 pela classe de elevacao HC1..HC4. Vh (m/s) limitado a
    1,5 (p.21). classe_hc: 'HC1'..'HC4'. Retorna Psi (float)."""
    hc = str(classe_hc).upper()
    if hc not in _TAB12:
        raise ValueError(f"classe de elevacao invalida: {classe_hc} ({list(_TAB12)})")
    beta2, psi_min = _TAB12[hc]
    v = max(0.0, min(float(Vh), VH_MAX))
    return psi_min + beta2 * v


def n_ciclos(classe_b):
    """Numero de ciclos de tensao (N) da classe de utilizacao do componente
    estrutural B0..B10 (NBR 8400-1:2019 Tabela 9). Representativo = LIMITE SUPERIOR
    do intervalo (conservador na fadiga). classe_b: 'B0'..'B10'. Retorna int."""
    b = str(classe_b).upper()
    if b not in _TAB9_SUP:
        raise ValueError(f"classe de utilizacao invalida: {classe_b} ({list(_TAB9_SUP)})")
    return _TAB9_SUP[b]


def _selftest():
    # Tabela 12 (verbatim) + formula Psi = Psi_min + beta2*Vh
    assert abs(coef_dinamico("HC1", 0.0) - 1.05) < 1e-9
    assert abs(coef_dinamico("HC4", 0.0) - 1.20) < 1e-9
    assert abs(coef_dinamico("HC4", 1.0) - (1.20 + 0.68)) < 1e-9
    assert coef_dinamico("HC2", 2.0) == coef_dinamico("HC2", VH_MAX)   # cap Vh
    assert abs(coef_dinamico("hc3", 0.5) - (1.15 + 0.51 * 0.5)) < 1e-9  # case-insensitive
    try:
        coef_dinamico("HC9", 0.5); raise AssertionError("deveria falhar")
    except ValueError:
        pass
    # Tabela 9 (verbatim) - limite superior conservador
    assert n_ciclos("B0") == 16_000
    assert n_ciclos("B7") == 2_000_000
    assert n_ciclos("B10") >= 8_000_000
    assert n_ciclos("B3") < n_ciclos("B6")
    print("[nbr8400 selftest] OK")


if __name__ == "__main__":
    _selftest()
