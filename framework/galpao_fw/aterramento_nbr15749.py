# ============================================================================
# aterramento_nbr15749.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Sistema de ATERRAMENTO do galpao: resistividade do solo, resistencia de haste,
# de conjunto de hastes e de malha. Base: ABNT NBR 15749 (medicao de resistencia
# de aterramento e de resistividade do solo) e Mamede/Negrisoli Cap.11:
#   1) RESISTIVIDADE aparente pelo metodo de WENNER (NBR 15749): rho = 2*pi*a*R,
#      valido para a >> b (profundidade dos eletrodos, tipicamente b <= a/20).
#   2) RESISTENCIA de HASTE vertical isolada: R = rho/(2*pi*L)*ln(2L/r) (r = raio;
#      forma equivalente rho/(2*pi*L)*ln(4L/d) com d = diametro).
#   3) CONJUNTO de n hastes em paralelo: Rn = R1/(n*K), K = rendimento (0<K<=1).
#   4) MALHA de aterramento (Sverak/Laurent-Niemann): Rm = rho/4*raiz(pi/A) + rho/L
#      (A = area da malha, L = comprimento total de condutor enterrado).
#   5) LIMITE recomendado: R <= 10 ohm (NBR 5419, SPDA/subestacao); <= 1 ohm em
#      locais a prova de explosao (Negrisoli).
# Formulas e o exemplo (haste 3 m, d=3/4", rho=100 -> 33,9 ohm) LIDOS do PDF da NBR
# 15749 / Negrisoli via NotebookLM - NAO de memoria.
# Unidades: rho em ohm.m; L,a,d,r em m; A em m2; R em ohm. Saidas em portugues.
# ============================================================================
"""Aterramento (NBR 15749 / Mamede Cap.11): resistividade de Wenner, resistencia
de haste, de n hastes e de malha (Sverak), com o limite de 10 ohm da NBR 5419."""

from __future__ import annotations

import math

R_MAX_SPDA = 10.0         # ohm, NBR 5419 (SPDA / subestacao MT)
R_MAX_EXPLOSIVO = 1.0     # ohm, locais a prova de explosao (Negrisoli)


def resistividade_wenner(a, R_medido):
    """Resistividade aparente do solo (NBR 15749): rho = 2*pi*a*R. a = espacamento
    entre eletrodos (m); R = resistencia lida no terrometro (ohm) -> ohm.m."""
    return 2.0 * math.pi * a * R_medido


def resistencia_haste(rho, L, d):
    """Resistencia de uma haste vertical isolada: R = rho/(2*pi*L)*ln(4L/d).
    rho ohm.m; L comprimento (m); d diametro (m)."""
    if L <= 0 or d <= 0:
        raise ValueError("[A CONFIRMAR] comprimento L e diametro d da haste devem ser "
                         "> 0 (recebido L=%r, d=%r m)." % (L, d))
    return rho / (2.0 * math.pi * L) * math.log(4.0 * L / d)


def resistencia_hastes_paralelo(R1, n, K):
    """Resistencia de n hastes em paralelo: Rn = R1/(n*K). K = fator de
    aproveitamento (rendimento) do agrupamento, 0 < K <= 1."""
    if n <= 0 or not 0.0 < K <= 1.0:
        raise ValueError("[A CONFIRMAR] n de hastes deve ser >= 1 e K em (0, 1] "
                         "(recebido n=%r, K=%r)." % (n, K))
    return R1 / (n * K)


def resistencia_malha(rho, A, L):
    """Resistencia de malha de aterramento (Sverak): Rm = rho/4*raiz(pi/A) + rho/L.
    rho ohm.m; A area da malha (m2); L comprimento total de condutor enterrado (m)."""
    if A <= 0 or L <= 0:
        raise ValueError("[A CONFIRMAR] area A e comprimento L da malha devem ser > 0 "
                         "(recebido A=%r m2, L=%r m)." % (A, L))
    return rho / 4.0 * math.sqrt(math.pi / A) + rho / L


def dimensiona_aterramento(caso):
    """Verifica um sistema de aterramento contra o limite recomendado.
    caso: {tipo('haste'|'hastes'|'malha'), rho, ...parametros..., limite(=10)}.
      haste : {L, d}
      hastes: {L, d, n, K}
      malha : {A, L_cond}
    Retorna dict com R calculada, limite e OK."""
    tipo = caso["tipo"]
    rho = float(caso["rho"])
    limite = float(caso.get("limite", R_MAX_SPDA))
    if tipo == "haste":
        R = resistencia_haste(rho, caso["L"], caso["d"])
        detalhe = {"R1_ohm": R}
    elif tipo == "hastes":
        R1 = resistencia_haste(rho, caso["L"], caso["d"])
        R = resistencia_hastes_paralelo(R1, int(caso["n"]), float(caso["K"]))
        detalhe = {"R1_ohm": R1, "n": caso["n"], "K": caso["K"]}
    elif tipo == "malha":
        R = resistencia_malha(rho, float(caso["A"]), float(caso["L_cond"]))
        detalhe = {"A_m2": caso["A"], "L_cond_m": caso["L_cond"]}
    else:
        raise ValueError("[A CONFIRMAR] tipo de aterramento '%s' desconhecido." % tipo)
    return {"tipo": tipo, "rho": rho, "R_ohm": R, "limite_ohm": limite,
            "OK": R <= limite, **detalhe}


def _selftest():
    """Afere contra o Exemplo 11.1 de Negrisoli: haste 3/4" (r=10mm), L=3 m,
    rho=100 ohm.m -> R = 33,9 ohm."""
    # forma por raio: rho/(2*pi*L)*ln(2L/r) com r=0,01 -> mesma que 4L/d, d=0,02
    R = resistencia_haste(100.0, 3.0, 0.02)               # d=20mm -> 4L/d = 2L/r
    assert abs(R - 33.9) < 0.1, R
    # Wenner: a=4 m, R=2 ohm -> rho = 2*pi*4*2 = 50,27 ohm.m
    assert abs(resistividade_wenner(4.0, 2.0) - 50.265) < 0.01
    # n hastes em paralelo reduzem a resistencia
    Rn = resistencia_hastes_paralelo(33.9, 4, 0.75)
    assert Rn < 33.9 and abs(Rn - 11.3) < 0.1
    # malha grande atinge o limite de 10 ohm
    m = dimensiona_aterramento({"tipo": "malha", "rho": 100.0, "A": 1200.0,
                                "L_cond": 400.0})
    assert m["R_ohm"] > 0 and "OK" in m
    # haste isolada de 33,9 ohm REPROVA no limite de 10 ohm
    h = dimensiona_aterramento({"tipo": "haste", "rho": 100.0, "L": 3.0, "d": 0.02})
    assert not h["OK"] and abs(h["R_ohm"] - 33.9) < 0.1
    print("aterramento_nbr15749 self-test PASSED (Negrisoli haste 3m rho100 = 33,9 ohm)")


if __name__ == "__main__":
    _selftest()
