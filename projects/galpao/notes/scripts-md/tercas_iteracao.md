# Gate 7 - Iteracao de tercas Ue - tercas_iteracao.py

Arquivo: `projects/galpao/calc/tercas_iteracao.py`  
Gerado: 2026-07-05  
Driver do projeto: itera escada Ue, calcula Mdist (FSM) e props (linha
media) de cada, adota o mais leve que passa (NBR 14762).

## Codigo completo

```python
# ============================================================================
# tercas_iteracao.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Itera uma ESCADA de perfis Ue (formados a frio) e adota o mais leve que PASSA
# na verificacao da terca (NBR 14762), para o galpao atual. Para cada candidato:
#   - Propriedades da secao pela LINHA MEDIA (prop2 do pycufsm) - A, Ix, Iy, Wx,
#     Wy - em vez de valores de catalogo (A CONFIRMAR com o fabricante).
#   - Mdist (flambagem distorcional elastica) via distorcional_fsm (FSM).
#   - verifica_terca (tercas_nbr14762): MSE local, Anexo F (sucao), distorcional,
#     cortante, flexao obliqua e flecha (ELS).
# Config do galpao: vao = espacamento de porticos ; linha de corrente no meio ;
# largura de influencia da agua ; cargas caracteristicas G/Q/W (vento do modulo
# vento_nbr6123). Requer numpy<2 (pycufsm). Saidas em portugues.
# ============================================================================
"""Iteracao de terças Ue para o galpao. Usa distorcional_fsm + tercas_nbr14762."""

from __future__ import annotations

import math
import re

import distorcional_fsm as fsm
import tercas_nbr14762 as tc
import vento_nbr6123 as vento
from pycufsm.pre.cutwp import prop2

FY = 250e3          # ZAR-250 (fy=250 MPa) - confirmar o aco
BAY = 5.0           # vao da terca (espacamento de porticos), m
LY = 2.5            # eixo fraco (linha de corrente no meio-vao), m
TRIB = 1.675        # largura de influencia da agua, m
THETA = math.atan(0.5 / 5.0)

# escada Ue (bw x bf x D x t, mm) do mais leve ao mais pesado
ESCADA = [
    (150., 60., 20., 2.00), (200., 75., 20., 2.00), (200., 75., 25., 2.65),
    (250., 85., 25., 3.00), (300., 85., 25., 3.35),
]


def _props_ue(bw, bf, D, t):
    """Propriedades da linha media via prop2 (mm) -> SI. A CONFIRMAR catalogo."""
    coord, ends = fsm.secao_ue(bw, bf, D, t)
    sp = prop2(coord, ends)
    cx, cy = sp["cx"], sp["cy"]
    ymax = max(abs(coord[:, 1] - cy))
    xmax = max(abs(coord[:, 0] - cx))
    return {
        "nome": f"Ue {bw:.0f}x{bf:.0f}x{D:.0f}x{t:.2f}",
        "bw": bw, "bf": bf, "D": D, "t": t, "r": 0.0, "secao": "U",
        "A": sp["A"] * 1e-6, "Ix": sp["Ixx"] * 1e-12, "Iy": sp["Iyy"] * 1e-12,
        "Wx": (sp["Ixx"] / ymax) * 1e-9, "Wy": (sp["Iyy"] / xmax) * 1e-9,
        "peso": sp["A"],           # ~ area (proxy do peso linear)
    }


def _sucao_caracteristica():
    """Pior sucao caracteristica na cobertura (kN/m2) do vento_nbr6123."""
    r = vento.compute()
    q = r["q_kN_m2"]
    piores = []
    for caso, d in r["net"].items():
        for sup, cp in d.items():
            if "cobertura" in sup:
                piores.append(cp * q)
    return min(piores)          # mais negativo = maior sucao


def avalia(bw, bf, D, t):
    perfil = _props_ue(bw, bf, D, t)
    md = fsm.mdist(bw, bf, D, t, fy=FY / 1000.0)      # kN.m
    cfg = {"fy": FY, "theta": THETA, "vao": BAY, "vao_fraco": LY,
           "larg_influencia": TRIB, "continua": False,
           "G": 0.10, "Q": 0.25, "W": _sucao_caracteristica(),
           "Mdist": md.get("Mdist_kNm")}
    res = tc.verifica_terca(perfil, cfg)
    ok = all(c["OK"] for c in res["casos"].values()) and \
        res["els"]["ok_grav"] and res["els"]["ok_vento"]
    inter = max(c["interacao"] for c in res["casos"].values())
    return {"perfil": perfil["nome"], "peso": perfil["peso"], "Mdist": md.get("Mdist_kNm"),
            "dispensa": res["dispensa_dist"], "interacao": inter,
            "flecha_v": res["els"]["d_vento"] * 1000, "OK": ok, "res": res, "cfg": cfg}


def memoria_pt():
    W = _sucao_caracteristica()
    L = ["=" * 74,
         "GATE 7 - ITERACAO DE TERCAS Ue (NBR 14762) - GALPAO 20x10",
         "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO ; PROPRIEDADES A CONFIRMAR", "=" * 74,
         f"Vao {BAY:.1f} m ; linha de corrente no meio (Ly={LY:.1f} m) ; "
         f"trib {TRIB:.3f} m ; inclinacao {math.degrees(THETA):.2f} graus",
         f"Cargas caract.: G=0,10 Q=0,25 W={W:+.3f} kN/m2 (pior sucao do vento) ; "
         f"aco fy={FY/1000:.0f} MPa", "",
         f"{'Perfil':>18} {'Mdist':>7} {'disp?':>5} {'inter':>6} {'flecha_v':>9} | resultado",
         "-" * 74]
    adotado = None
    for bw, bf, D, t in ESCADA:
        r = avalia(bw, bf, D, t)
        tag = "PASSA" if r["OK"] else "nao passa"
        if r["OK"] and adotado is None:
            adotado = r
        md = f"{r['Mdist']:.1f}" if r["Mdist"] else "-"
        dsp = "sim" if r["dispensa"] else "nao"
        L.append(f"{r['perfil']:>18} {md:>7} {dsp:>5} {r['interacao']:6.2f} "
                 f"{r['flecha_v']:7.1f}mm | {tag}")
    L += ["-" * 74, ""]
    if adotado:
        L += [f"ADOTADO (mais leve que passa): {adotado['perfil']}",
              f"  interacao max = {adotado['interacao']:.2f} ; "
              f"flecha vento = {adotado['flecha_v']:.1f} mm ; "
              f"Mdist = {adotado['Mdist']:.1f} kN.m"]
    else:
        L += ["NENHUM da escada passou - ampliar a lista ou rever o esquema (mais",
              "linhas de corrente, telha auto-portante, reduzir o vao)."]
    L += ["", "OBS: propriedades pela linha media (prop2) - A CONFIRMAR no catalogo",
          "     do fornecedor. Mdist pela analise de estabilidade elastica (FSM)."]
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


if __name__ == "__main__":
    print(memoria_pt())
```

## Resultado da execucao

```
==========================================================================
GATE 7 - ITERACAO DE TERCAS Ue (NBR 14762) - GALPAO 20x10
CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO ; PROPRIEDADES A CONFIRMAR
==========================================================================
Vao 5,0 m ; linha de corrente no meio (Ly=2,5 m) ; trib 1,675 m ; inclinacao 5,71 graus
Cargas caract.: G=0,10 Q=0,25 W=-1,362 kN/m2 (pior sucao do vento) ; aco fy=250 MPa

            Perfil   Mdist disp?  inter  flecha_v | resultado
--------------------------------------------------------------------------
 Ue 150x60x20x2,00    18,5   nao   2,00    38,2mm | nao passa
 Ue 200x75x20x2,00    19,6   nao   1,35    18,0mm | nao passa
 Ue 200x75x25x2,65    42,8   nao   0,95    12,7mm | PASSA
 Ue 250x85x25x3,00    60,4   nao   0,95     6,2mm | PASSA
 Ue 300x85x25x3,35    86,3   nao   0,27     3,7mm | PASSA
--------------------------------------------------------------------------

ADOTADO (mais leve que passa): Ue 200x75x25x2,65
  interacao max = 0,95 ; flecha vento = 12,7 mm ; Mdist = 42,8 kN.m

OBS: propriedades pela linha media (prop2) - A CONFIRMAR no catalogo
     do fornecedor. Mdist pela analise de estabilidade elastica (FSM).
```
