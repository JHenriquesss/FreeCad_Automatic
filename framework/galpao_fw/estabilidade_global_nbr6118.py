# ============================================================================
# estabilidade_global_nbr6118.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Estabilidade GLOBAL de estruturas de concreto (NBR 6118:2014, item 15.5):
# decide se os esforcos globais de 2a ordem podem ser DISPENSADOS (estrutura de
# "nos fixos") ou se precisam ser considerados ("nos moveis").
#   - PARAMETRO DE INSTABILIDADE alpha (15.5.2): alpha = Htot*sqrt(Nk/(Ecs*Ic)).
#     Nos fixos se alpha <= alpha1, com alpha1 = 0,2+0,1n (n<=3) ou 0,6 (n>=4).
#     Para o GALPAO pre-moldado (pilares em balanco, n=1 pavimento): alpha1 = 0,3.
#     Na estabilidade global o Ecs pode ser majorado em 10% (15.5.2).
#   - COEFICIENTE gamma_z (15.5.3): gamma_z = 1/(1 - dMtot,d/M1,tot,d). Valido
#     APENAS para estruturas reticuladas de NO MINIMO 4 andares -> nao se aplica
#     ao galpao terreo (o modulo devolve gamma_z mas sinaliza a inaplicabilidade).
#   - Majoracao 0,95*gamma_z (15.7.2) quando 1,1 < gamma_z <= 1,3.
# Formulas/limites lidos do PDF NBR 6118:2014 (NotebookLM), nao de memoria.
# Unidades: m, kN (fck/Ecs em kN/m2).
# ============================================================================
"""Estabilidade global (NBR 6118 15.5): parametro alpha, classificacao de nos
fixos/moveis e coeficiente gamma_z."""

from __future__ import annotations

import math

import fissuracao_nbr6118 as fis


def alpha_limite(n_andares, sistema="portico"):
    """Valor-limite alpha1 (15.5.2). n_andares = niveis de barras horizontais
    acima da fundacao. Para n<=3: 0,2+0,1n ; n>=4: 0,6. Ressalvas por sistema de
    contraventamento (so porticos 0,5 ; pilares-parede 0,7 ; assoc. 0,6)."""
    if n_andares >= 4:
        return {"portico": 0.5, "pilar_parede": 0.7, "associado": 0.6}.get(sistema, 0.6)
    return 0.2 + 0.1 * n_andares


def parametro_alpha(H, Nk, Ecs, Ic, majora_ecs=True):
    """Parametro de instabilidade alpha (15.5.2): alpha = H*sqrt(Nk/(Ecs*Ic)).
    H = altura total (m) ; Nk = soma das acoes verticais CARACTERISTICAS (kN) ;
    Ecs*Ic = rigidez do pilar equivalente engastado-livre (kN.m2). Na analise
    global, Ecs majorado em 10%."""
    E = 1.1 * Ecs if majora_ecs else Ecs
    return H * math.sqrt(Nk / (E * Ic))


def classifica_nos(alpha, alpha1):
    return "fixos" if alpha <= alpha1 else "moveis"


def gamma_z(dM_tot_d, M1_tot_d):
    """Coeficiente gamma_z (15.5.3) = 1/(1 - dMtot,d/M1,tot,d).
    M1,tot,d = momento de tombamento (forcas horizontais de calculo x base) ;
    dMtot,d = soma (forcas verticais de calculo x deslocamentos horizontais 1a ordem)."""
    return 1.0 / (1.0 - dM_tot_d / M1_tot_d)


def majoracao_horizontal(gz):
    """Fator de majoracao dos esforcos horizontais (15.7.2): 0,95*gamma_z, valido
    para 1,1 < gamma_z <= 1,3. Abaixo de 1,1 nao precisa; acima de 1,3 nao vale
    o processo simplificado (fazer P-Delta)."""
    if gz <= 1.1:
        return 1.0, "gamma_z <= 1,1: 2a ordem global dispensavel"
    if gz <= 1.3:
        return 0.95 * gz, "majorar esforcos horizontais por 0,95 gamma_z (15.7.2)"
    return None, "gamma_z > 1,3: processo simplificado invalido - exige P-Delta"


def inercia_retangular(b, h):
    """Inercia a flexao de uma secao retangular no plano de flexao de altura h."""
    return b * h ** 3 / 12.0


def verifica_estabilidade_galpao(H, Nk, b_col, h_col, n_col, fck, n_andares=1):
    """Estabilidade global de um portico de galpao pre-moldado (pilares em balanco)
    numa direcao. h_col = dimensao do pilar NO PLANO do deslocamento (// vento).
    Nk = soma das cargas verticais CARACTERISTICAS do portico. n_col = nº de pilares
    do portico (2). Devolve alpha, alpha1 e a classificacao de nos."""
    Ecs = fis.modulo_secante(fck)
    Ic = n_col * inercia_retangular(b_col, h_col)          # rigidez somada dos pilares
    a = parametro_alpha(H, Nk, Ecs, Ic)
    a1 = alpha_limite(n_andares, "portico")
    nos = classifica_nos(a, a1)
    return {"alpha": round(a, 3), "alpha1": round(a1, 3), "nos": nos,
            "Ecs_MPa": round(Ecs / 1000.0, 0), "Ic_m4": round(Ic, 5),
            "dispensa_2a_ordem_global": nos == "fixos",
            "gamma_z_aplicavel": n_andares >= 4,
            "OK": nos == "fixos", "n_andares": n_andares}


def relatorio_pt(r):
    L = ["ESTABILIDADE GLOBAL (NBR 6118 15.5.2, parametro de instabilidade)",
         f"  alpha = {r['alpha']:.3f} {'<=' if r['nos']=='fixos' else '>'} alpha1 = {r['alpha1']:.2f} "
         f"-> NOS {r['nos'].upper()}",
         f"  {'2a ordem global DISPENSAVEL (nos fixos)' if r['dispensa_2a_ordem_global'] else '2a ordem global a CONSIDERAR (nos moveis)'}"
         + ("" if r["gamma_z_aplicavel"] else " ; gamma_z nao se aplica (<4 andares) - usar alpha")]
    import re
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # portico de galpao: 2 pilares 20x40 (hx=0,40 // vento), H=6 m, Nk=80 kN, C30
    r = verifica_estabilidade_galpao(6.0, 80.0, 0.20, 0.40, 2, 30e3)
    assert r["alpha1"] == 0.3                       # n=1 -> 0,2+0,1
    assert r["nos"] in ("fixos", "moveis")
    assert r["alpha"] > 0
    # carga vertical baixa (galpao leve) -> alpha pequeno -> nos fixos
    assert r["nos"] == "fixos", r
    # muita carga vertical -> alpha cresce (pode virar nos moveis)
    r_pesado = verifica_estabilidade_galpao(6.0, 5000.0, 0.20, 0.40, 2, 30e3)
    assert r_pesado["alpha"] > r["alpha"]
    # alpha1 por nº de andares (15.5.2)
    assert abs(alpha_limite(1) - 0.3) < 1e-9 and abs(alpha_limite(3) - 0.5) < 1e-9
    assert abs(alpha_limite(4) - 0.5) < 1e-9 and abs(alpha_limite(2) - 0.4) < 1e-9
    # gamma_z e majoracao (15.5.3 / 15.7.2)
    gz = gamma_z(100.0, 1000.0)                      # 1/(1-0,1) = 1,111
    assert abs(gz - 1.0 / 0.9) < 1e-9
    f, _ = majoracao_horizontal(1.2)
    assert abs(f - 0.95 * 1.2) < 1e-9
    assert majoracao_horizontal(1.05)[0] == 1.0
    assert majoracao_horizontal(1.4)[0] is None
    print("estabilidade_global_nbr6118 self-test PASSED")
    print(relatorio_pt(r))


if __name__ == "__main__":
    _selftest()
