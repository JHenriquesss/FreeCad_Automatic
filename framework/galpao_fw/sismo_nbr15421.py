# ============================================================================
# sismo_nbr15421.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Acao SISMICA pelo METODO DAS FORCAS HORIZONTAIS EQUIVALENTES da ABNT NBR
# 15421:2023 (Secao 9). Fecha a lacuna da acao de sismo em galpao. Metodo e
# constantes LIDOS DO PDF em pesquisa/aco/ (NAO de memoria).
#
#   - Zoneamento (Tab.1): zona sismica -> ag (aceleracao horizontal caracteristica
#     normalizada, em fracao de g). Zona 0..4.
#   - Categoria sismica (Tab.5): zona 0/1 -> A ; 2 -> B ; 3/4 -> C.
#       zona 0: NENHUM requisito sismico. zona 1 (cat.A): metodo simplificado
#       Fx = 0,01*wx (7.3.2). zonas 2-4 (cat.B/C): metodo das forcas horizontais
#       equivalentes (Secao 9).
#   - Classe do terreno (Tab.2) -> fatores de amplificacao Ca, Cv (Tab.3).
#   - Espectro de projeto Sa(T) (6.3): ags0=Ca*ag ; ags1=Cv*0,75*ag ; 4 trechos.
#   - Forca horizontal total (9.1): H = Cs*W , W = peso efetivo.
#       Cs = 2,5*ags0/(R/I) ; <= ags1/(T*(R/I)) ; >= 0,01.
#   - Periodo aproximado (9.2): Ta = CT*hn^x (CT,x por sistema; cap Cup, Tab.10).
#   - Distribuicao vertical (9.3): Fx = Cvx*H ; Cvx = wx*hx^k / sum(wi*hi^k) ;
#       k=1 (T<0,5s) / (T+1,5)/2 (0,5-2,5s) / 2 (T>2,5s). Galpao 1 nivel = trivial.
#   - R (Tab.6): coef. de modificacao de resposta (aco momento 3,5 ; aco treli-
#     cado 3,25 ; ...). I (Tab.4): fator de importancia (1,0/1,25/1,50).
#
# ag (zona), classe do terreno, R (sistema), I (categoria de utilizacao), W (peso
# efetivo) e hn (altura) = DADOS DO PROJETO/SITIO (Ask, Do Not Invent) - a skill
# confirma. Saidas em portugues. Unidades: kN, m ; ag em fracao de g. CONCEITUAL.
# ============================================================================
"""Acao sismica (NBR 15421:2023) pelo metodo das forcas horizontais equivalentes."""

from __future__ import annotations

import math
import re

# ag representativo (limite superior da faixa) por zona sismica - Tabela 1. O
# valor exato de ag vem do mapa de zoneamento/sitio (a skill confirma); estes sao
# os tetos das faixas, uso conservador quando so se conhece a zona.
ZONA_AG = {0: 0.025, 1: 0.05, 2: 0.10, 3: 0.15, 4: 0.15}

# Categoria sismica por zona - Tabela 5.
ZONA_CATEGORIA = {0: "A", 1: "A", 2: "B", 3: "C", 4: "C"}

# Fatores de amplificacao no solo Ca, Cv - Tabela 3. Colunas: ag<=0,10g e ag=0,15g
# (interpolar linear entre 0,10 e 0,15). Classe F exige estudo especifico.
_CA = {"A": (0.8, 0.8), "B": (1.0, 1.0), "C": (1.2, 1.2),
       "D": (1.6, 1.5), "E": (2.5, 2.1)}
_CV = {"A": (0.8, 0.8), "B": (1.0, 1.0), "C": (1.7, 1.7),
       "D": (2.4, 2.2), "E": (3.5, 3.4)}

# Coeficientes de projeto por sistema sismorresistente - Tabela 6: (R, Omega0, Cd).
SISTEMA_R = {
    "aco_momento": (3.5, 3.0, 3.0),        # porticos de aco momento-resistentes
    "aco_trelicado": (3.25, 2.0, 3.25),    # porticos de aco contraventados em trelica
    "concreto_portico": (3.0, 3.0, 2.5),
    "misto": (3.0, 3.0, 2.5),
    "pendulo_invertido": (2.5, 2.0, 2.5),  # pilares em balanco (galpao rotulado!)
    "dual": (4.5, 2.5, 4.0),
}

# Coeficientes de periodo (9.2): (CT, x) por sistema.
_CT_X = {
    "aco_momento": (0.0724, 0.8),
    "aco_trelicado": (0.0731, 0.75),
    "concreto_portico": (0.0466, 0.9),
    "outras": (0.0488, 0.75),
}
# Coeficiente de limitacao do periodo Cup - Tabela 10 (zonas 2,3,4).
_CUP = {2: 1.7, 3: 1.6, 4: 1.5}

G = 9.80665                 # aceleracao da gravidade (m/s2) - referencia


def coef_ca_cv(ag, classe):
    """Fatores de amplificacao no solo Ca, Cv (Tabela 3), interpolados para
    0,10g < ag < 0,15g. ag em fracao de g. Retorna (Ca, Cv)."""
    ca10, ca15 = _CA[classe]
    cv10, cv15 = _CV[classe]
    if ag <= 0.10:
        return ca10, cv10
    if ag >= 0.15:
        return ca15, cv15
    t = (ag - 0.10) / 0.05                       # interpolacao linear
    return ca10 + t * (ca15 - ca10), cv10 + t * (cv15 - cv10)


def espectro_sa(T, ag, classe):
    """Espectro de resposta de projeto Sa(T) (6.3), em fracao de g. Quatro trechos
    (T em s). ag em fracao de g. ags0=Ca*ag ; ags1=Cv*0,75*ag."""
    Ca, Cv = coef_ca_cv(ag, classe)
    ags0 = Ca * ag
    ags1 = Cv * 0.75 * ag
    t1 = 0.04 * Cv / Ca
    t2 = 0.30 * Cv / Ca
    t3 = 2.0 * Cv / Ca
    if T <= t1:
        return ags0 * (37.5 * T * Ca / Cv + 1.0)
    if T <= t2:
        return 2.5 * ags0
    if T <= t3:
        return ags1 / T
    return 2.0 * (Cv / Ca) * ags1 / (T ** 2)


def periodo_aproximado(hn, sistema="aco_momento", zona=None):
    """Periodo natural aproximado Ta = CT*hn^x (9.2). hn = altura acima da base (m).
    Retorna Ta (s). (O Cup so limita o T de extracao modal, nao o proprio Ta.)"""
    CT, x = _CT_X.get(sistema, _CT_X["outras"])
    return CT * hn ** x


def coef_resposta_cs(ag, classe, R, I, T):
    """Coeficiente de resposta sismica Cs (9.1). ags0/ags1 em fracao de g -> Cs
    adimensional (fracao de W). Cs = 2,5*ags0/(R/I) <= ags1/(T*(R/I)) >= 0,01."""
    Ca, Cv = coef_ca_cv(ag, classe)
    ags0 = Ca * ag
    ags1 = Cv * 0.75 * ag
    RI = R / I
    cs = 2.5 * ags0 / RI
    cs_cap = ags1 / (T * RI) if T > 0 else float("inf")
    cs = min(cs, cs_cap)
    return max(cs, 0.01), cs_cap


def _k_distribuicao(T):
    """Expoente de distribuicao vertical k (9.3)."""
    if T < 0.5:
        return 1.0
    if T <= 2.5:
        return (T + 1.5) / 2.0
    return 2.0


def verifica_sismo(W, zona, classe="C", sistema="aco_momento", I=1.0,
                   hn=None, ag=None, R=None, pesos_niveis=None, alturas=None):
    """Acao sismica pelo metodo das forcas horizontais equivalentes (NBR 15421).

    W = peso efetivo total (kN) ; zona = zona sismica (0..4) ; classe = classe do
    terreno (A..E) ; sistema = sistema sismorresistente (chave de SISTEMA_R) ;
    I = fator de importancia (Tab.4) ; hn = altura acima da base (m) ; ag = acele-
    racao (fracao de g; default = teto da faixa da zona) ; R = coef. de resposta
    (default da Tab.6 pelo sistema). pesos_niveis/alturas: listas para distribuir
    Fx (default: 1 nivel = tudo em hn). Unidades: kN, m. Retorna dict.

    Categoria (Tab.5): zona 0 -> dispensado ; zona 1 (cat.A) -> Fx=0,01*wx ;
    zonas 2-4 (cat.B/C) -> metodo completo."""
    cat = ZONA_CATEGORIA[zona]
    ag = ag if ag is not None else ZONA_AG[zona]
    r = {"zona": zona, "categoria": cat, "ag": ag, "classe": classe,
         "sistema": sistema, "I": I, "W": W, "hn": hn}

    if zona == 0:                                # 7.3.2: nenhum requisito
        r.update(dispensado=True, metodo="dispensado (zona 0)", H=0.0,
                 OK=True)
        return r
    if zona == 1:                                # 7.3.2: simplificado Fx=0,01 wx
        H = 0.01 * W
        r.update(dispensado=False, metodo="simplificado cat.A (Fx=0,01*wx)",
                 Cs=0.01, H=H, R=None, T=None, OK=True)
        return r

    # zonas 2-4: metodo das forcas horizontais equivalentes (Secao 9)
    if R is None:
        R = SISTEMA_R[sistema][0]
    if hn is None:
        raise ValueError("hn (altura) obrigatorio para o metodo da Secao 9")
    T = periodo_aproximado(hn, sistema, zona)
    Cs, Cs_cap = coef_resposta_cs(ag, classe, R, I, T)
    H = Cs * W
    Ca, Cv = coef_ca_cv(ag, classe)
    k = _k_distribuicao(T)
    # distribuicao vertical Fx = Cvx*H
    if pesos_niveis and alturas:
        soma = sum(w * h ** k for w, h in zip(pesos_niveis, alturas))
        Fx = [(w * h ** k / soma) * H for w, h in zip(pesos_niveis, alturas)]
    else:
        Fx = [H]                                 # 1 nivel (galpao): tudo no topo
    r.update(dispensado=False, metodo="forcas horizontais equivalentes (Secao 9)",
             R=R, T=T, Cs=Cs, Cs_cap=Cs_cap, Ca=Ca, Cv=Cv, ags0=Ca * ag,
             ags1=Cv * 0.75 * ag, k=k, H=H, Fx=Fx, OK=True)
    return r


def relatorio_pt(r):
    L = ["=" * 70, "ACAO SISMICA - NBR 15421:2023 (forcas horizontais equivalentes)",
         "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 70, "",
         f"Zona sismica: {r['zona']} (ag={r['ag']:.3f} g) ; categoria sismica: "
         f"{r['categoria']} ; classe do terreno: {r['classe']}"]
    if r["zona"] == 0:
        L += ["", ">> Zona 0: NENHUM requisito de resistencia sismica (7.3.2). "
              "Dispensado."]
    elif r["zona"] == 1:
        L += ["", f">> Zona 1 (cat.A): metodo simplificado Fx = 0,01*wx -> "
              f"H = {r['H']:.1f} kN (0,01*W). Sistema resistente em 2 direcoes "
              "ortogonais + mecanismo de torcao (7.3.2)."]
    else:
        L += [f"Sistema: {r['sistema']} (R={r['R']}, I={r['I']}) ; hn={r['hn']:.1f} m",
              f"Periodo aproximado Ta = {r['T']:.3f} s (k={r['k']:.2f})",
              f"Espectro: ags0={r['ags0']:.3f} g ; ags1={r['ags1']:.3f} g "
              f"(Ca={r['Ca']:.2f}, Cv={r['Cv']:.2f})",
              f"Coef. de resposta Cs = {r['Cs']:.4f} (2,5*ags0/(R/I), cap "
              f"{r['Cs_cap']:.4f}, min 0,01)",
              "",
              f">> Forca horizontal total H = Cs*W = {r['H']:.1f} kN "
              f"(W={r['W']:.0f} kN)."]
        if len(r["Fx"]) > 1:
            L += ["   Distribuicao vertical Fx (topo->base): "
                  + " ; ".join(f"{f:.1f}" for f in r["Fx"]) + " kN"]
    L += ["", "[FLAG] zona/ag (mapa de zoneamento), classe do terreno (SPT/Vs30),",
          "       R (sistema) e I (categoria de utilizacao) = dados do sitio/projeto",
          "       - a skill confirma. Combinacao ultima EXCEPCIONAL (gamma_q=1,0)."]
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


def _selftest():
    # 1) espectro: no plato (0,04Cv/Ca <= T <= 0,3Cv/Ca) Sa = 2,5*ags0
    ag, classe = 0.15, "D"
    Ca, Cv = coef_ca_cv(ag, classe)                 # ag=0,15 -> Ca=1,5 ; Cv=2,2
    assert abs(Ca - 1.5) < 1e-9 and abs(Cv - 2.2) < 1e-9, (Ca, Cv)
    ags0 = Ca * ag
    t_meio = 0.5 * (0.04 + 0.30) * Cv / Ca          # dentro do plato
    assert abs(espectro_sa(t_meio, ag, classe) - 2.5 * ags0) < 1e-9
    # trecho descendente ags1/T
    ags1 = Cv * 0.75 * ag
    Tq = 1.0 * Cv / Ca                              # entre 0,3 e 2,0 Cv/Ca
    assert abs(espectro_sa(Tq, ag, classe) - ags1 / Tq) < 1e-9
    # 2) interpolacao Ca/Cv entre 0,10 e 0,15 (classe D: Ca 1,6->1,5)
    Ca12, _ = coef_ca_cv(0.125, "D")
    assert abs(Ca12 - 1.55) < 1e-9, Ca12
    # 3) Cs plato + cap + min. Zona 3 ag=0,15 classe D aco momento hn=8 I=1
    T = periodo_aproximado(8.0, "aco_momento")      # 0,0724*8^0,8
    assert abs(T - 0.0724 * 8.0 ** 0.8) < 1e-9
    Cs, cap = coef_resposta_cs(0.15, "D", 3.5, 1.0, T)
    cs_plato = 2.5 * (1.5 * 0.15) / 3.5
    assert abs(Cs - cs_plato) < 1e-6 and Cs >= 0.01, (Cs, cs_plato)
    # 4) verifica_sismo: zona 0 dispensa ; zona 1 = 0,01 W ; zona 3 = Cs*W
    r0 = verifica_sismo(1000.0, zona=0)
    assert r0["dispensado"] and r0["H"] == 0.0
    r1 = verifica_sismo(1000.0, zona=1)
    assert abs(r1["H"] - 10.0) < 1e-9 and r1["Cs"] == 0.01
    r3 = verifica_sismo(1000.0, zona=3, classe="D", sistema="aco_momento",
                        I=1.0, hn=8.0)
    assert abs(r3["H"] - r3["Cs"] * 1000.0) < 1e-9 and r3["H"] > 0
    assert abs(r3["Cs"] - cs_plato) < 1e-6
    print("sismo_nbr15421 self-test PASSED")
    print(f"  zona3 D aco-momento hn8: Ta={r3['T']:.3f}s ; Cs={r3['Cs']:.4f} ; "
          f"H={r3['H']:.1f} kN (W=1000)")


if __name__ == "__main__":
    _selftest()
    print()
    print(relatorio_pt(verifica_sismo(1200.0, zona=3, classe="D",
                                      sistema="aco_momento", I=1.0, hn=8.0)))
