# ============================================================================
# mao_francesa.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Dimensiona a CONTENCAO LATERAL da mesa inferior da viga (mao-francesa /
# flange brace) pela ABNT NBR 8800:2008, Anexo G (FLT). A mesa inferior do
# rafter e comprimida sob succao de vento (e junto ao joelho sob gravidade);
# a mao-francesa liga uma terca a essa mesa e cria um ponto de travamento,
# reduzindo o comprimento destravado Lb.
#
# Metodo (nao heuristica): inverte a VERIFICACAO DA BARRA (flexo-compressao
# 5.5.1.2), nao so o FLT puro. Reduzir Lb aumenta Nc,Rd (Ne do eixo fraco) e
# Mrd (FLT), logo a interacao e monotona crescente em Lb; por bissecao acha-se
# o MAIOR Lb tal que interacao <= 1,0. Esse Lb_max e o espacamento maximo entre
# maos-francesas. Dado o espacamento real das tercas ao longo da agua, deriva-se
# o "passo" (a cada quantas tercas colocar um braco) e o numero de bracos por
# portico. Se nem totalmente travada a barra passa, travar NAO resolve -> exige
# secao maior.
#
# NAO calcula esforcos (Nsd/Msd/Vsd vem do galpao_portico/estabilidade,
# amplificados de 2a ordem). Reusa check_nbr8800.verifica (mesma equacao de
# interacao do check da secao, garantindo consistencia).
# Calcula apenas; pendente revisao do eng. responsavel.
# ============================================================================
"""Espacamento da mao-francesa (mesa inferior) - inversao da interacao NBR 8800."""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_nbr8800 as ck


def _interacao(sec, fy, L, Nsd, Msd, Vsd, Lb, Cb):
    """Interacao flexo-compressao (5.5.1.2) da barra para um dado Lb."""
    r = ck.verifica(sec, fy, L=L, Nsd=Nsd, Msd=Msd, Vsd=Vsd,
                    Kx=1.0, Ky=1.0, Lb=Lb, Cb=Cb)
    return r["interacao"]


def lb_maximo(sec, fy, L, Nsd, Msd, Vsd, Cb=1.0, alvo=1.0, Lb_min=0.10):
    """Maior Lb (m) tal que a interacao (5.5.1.2) <= alvo (bissecao).

    Retorna (Lb_max, info). Lb_max=None se nem totalmente travada (Lb_min) a
    barra passa: travar nao resolve, exige secao maior.
    """
    _, _, d0 = ck.momento_resistente(sec, fy, Lb_min, Cb)
    info = {"Lp": d0["Lp"], "Lr_flt": d0["Lr_flt"],
            "interacao_travada": _interacao(sec, fy, L, Nsd, Msd, Vsd, Lb_min, Cb)}
    if info["interacao_travada"] > alvo:
        return None, info                      # nem totalmente travada passa
    lo, hi = Lb_min, Lb_min
    while _interacao(sec, fy, L, Nsd, Msd, Vsd, hi, Cb) <= alvo and hi < L:
        hi = min(hi * 1.5, L)
        if hi >= L:                            # travada so pelas pontas ja passa
            break
    if _interacao(sec, fy, L, Nsd, Msd, Vsd, hi, Cb) <= alvo:
        info["interacao_no_Lbmax"] = _interacao(sec, fy, L, Nsd, Msd, Vsd, hi, Cb)
        return hi, info                        # ate o comprimento total passa
    for _ in range(80):                        # bissecao lo(passa)..hi(nao passa)
        mid = 0.5 * (lo + hi)
        if _interacao(sec, fy, L, Nsd, Msd, Vsd, mid, Cb) <= alvo:
            lo = mid
        else:
            hi = mid
    info["interacao_no_Lbmax"] = _interacao(sec, fy, L, Nsd, Msd, Vsd, lo, Cb)
    return lo, info


def espacamento_terca_agua(span, slope, n_terca):
    """Espacamento das tercas ao longo da MEIA-AGUA (comprimento desenvolvido)."""
    meia = span / 2.0
    dev = meia * math.sqrt(1.0 + slope ** 2)   # comprimento inclinado da meia-agua
    return dev / n_terca                       # n_terca vaos de terca por agua


def plano_mao_francesa(sec, fy, Nsd, Msd, Vsd, span, slope, n_terca, Cb=1.0,
                       alvo=1.0):
    """Plano de contencao da mesa inferior por AGUA a partir da interacao.

    - stride: colocar 1 mao-francesa a cada `stride` tercas (>=1).
    - n_bracos_meia: bracos interiores por meia-agua = ceil(n_terca/stride)-1.
    - Lb_usado: maior tramo destravado resultante = min(stride,n_terca)*s_terca.
    Garante interacao(Lb_usado) <= alvo (verificacao final). O joelho
    (viga-coluna) e a cumeeira contam como pontos travados (sem braco).
    L (eixo forte) = comprimento desenvolvido da meia-agua.
    """
    s = espacamento_terca_agua(span, slope, n_terca)
    L = span / 2.0 * math.sqrt(1.0 + slope ** 2)
    Lbmax, info = lb_maximo(sec, fy, L, Nsd, Msd, Vsd, Cb, alvo)
    r = {"s_terca": s, "L_agua": L, "Lb_max": Lbmax, "Nsd": Nsd, "Msd": Msd,
         "Vsd": Vsd, "Cb": Cb, "alvo": alvo, **info}
    if Lbmax is None:
        r.update(ok=False, motivo="interacao > alvo mesmo totalmente travada: "
                 "travar nao resolve, aumentar a secao", stride=None,
                 n_bracos_meia=None, n_bracos_portico=None, Lb_usado=None)
        return r
    stride = max(1, int(Lbmax // s))           # quantas tercas por braco
    stride = min(stride, n_terca)              # nao passa da meia-agua
    Lb_usado = min(stride, n_terca) * s
    n_bracos_meia = int(math.ceil(n_terca / stride)) - 1   # divisoes interiores
    r.update(stride=stride, n_bracos_meia=n_bracos_meia,
             n_bracos_portico=2 * n_bracos_meia, Lb_usado=Lb_usado,
             interacao_usado=_interacao(sec, fy, L, Nsd, Msd, Vsd, Lb_usado, Cb))
    r["ok"] = r["interacao_usado"] <= alvo + 1e-9
    return r


def relatorio_pt(plano, sec_nome=""):
    p = plano
    L = ["=" * 68,
         f"MAO-FRANCESA (contencao da mesa inferior) - {sec_nome}".rstrip(),
         "NBR 8800 5.5.1.2 - espacamento por inversao da interacao flexo-compressao",
         "=" * 68,
         f"  Esforcos na mesa comprimida . Nsd={p['Nsd']:.1f} kN ; "
         f"Msd={p['Msd']:.1f} kN.m ; Vsd={p['Vsd']:.1f} kN",
         f"  Comprimento da meia-agua L .. {p['L_agua']:.3f} m",
         f"  Espacamento das tercas s .... {p['s_terca']:.3f} m",
         f"  Lp (plastico) ............... {p['Lp']:.3f} m",
         f"  Lr (FLT elastico) ........... {p['Lr_flt']:.3f} m",
         f"  Interacao totalmente travada. {p['interacao_travada']:.3f}"]
    if not p["ok"] and p["Lb_max"] is None:
        L += ["  >> NAO PASSA: " + p["motivo"]]
    else:
        L += [f"  Lb_max (interacao={p['alvo']:.2f}) ..... {p['Lb_max']:.3f} m",
              f"  Passo adotado ............... 1 braco a cada {p['stride']} terca(s)",
              f"  Lb usado (maior tramo) ...... {p['Lb_usado']:.3f} m",
              f"  Interacao em Lb_usado ....... {p['interacao_usado']:.3f} "
              f"({'OK' if p['ok'] else 'NAO'})",
              f"  Bracos por meia-agua ........ {p['n_bracos_meia']}",
              f"  Bracos por portico .......... {p['n_bracos_portico']}"]
    L.append("=" * 68)
    return "\n".join(L)


def _selftest():
    # Referencia: viga HEA180, aco MR250, combinacao de succao no joelho
    # (Nsd=39,8 kN ; Msd=61,3 kN.m ; Vsd=20,8 kN), galpao 10 m de vao, 10% de
    # inclinacao, 3 vaos de terca por agua.
    HEA180 = {"A": 45.25e-4, "Ix": 2510e-8, "Iy": 924.6e-8, "ry": 0.0452,
              "Zx": 324.9e-6, "Wx": 293.6e-6, "d": 0.171, "bf": 0.180,
              "tf": 0.0095, "tw": 0.006}
    p = plano_mao_francesa(HEA180, 250e3, 39.8, 61.3, 20.8,
                           span=10.0, slope=0.10, n_terca=3)
    print(relatorio_pt(p, "HEA180"))
    assert p["ok"], "interacao(Lb_usado) deve satisfazer o alvo"
    assert p["Lb_usado"] <= p["Lb_max"] + 1e-9
    assert p["interacao_usado"] <= 1.0 + 1e-9
    assert p["stride"] >= 1 and p["n_bracos_meia"] >= 0
    # Msd maior (mas ainda passavel travado): exige Lb_usado menor -> mais bracos
    p2 = plano_mao_francesa(HEA180, 250e3, 39.8, 72.0, 20.8,
                            span=10.0, slope=0.10, n_terca=3)
    assert p2["ok"] and p2["Lb_usado"] <= p2["Lb_max"] + 1e-9
    assert p2["Lb_max"] <= p["Lb_max"] and p2["Lb_usado"] <= p["Lb_usado"]
    # Esforco absurdo -> nem totalmente travada passa
    p3 = plano_mao_francesa(HEA180, 250e3, 39.8, 1e4, 20.8,
                            span=10.0, slope=0.10, n_terca=3)
    assert p3["ok"] is False and p3["Lb_max"] is None
    print("\n[selftest] OK")


if __name__ == "__main__":
    _selftest()
