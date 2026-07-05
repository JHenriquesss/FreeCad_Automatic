# galpao_portico.py

Analise do portico transversal + combinacoes NBR 8800 + memoria. Barras malhadas (momento no vao), vento normal a superficie, G sem cos.

CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO. Codigo em ingles; saidas em PT.

## Codigo

```python
# ============================================================================
# galpao_portico.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Monta o portico transversal do galpao e calcula os esforcos e deslocamentos.
#   Casos de carga: permanente (G), sobrecarga (Q) e vento (W, do vento_nbr6123).
#   Combinacoes ELU da NBR 8800 (gamma e psi0 das Tabelas 1 e 2).
#   Calcula: envoltoria de esforcos (M, N, V) em coluna e viga por combinacao
#            (momento avaliado AO LONGO da barra, nao so nos nos - barras malhadas),
#            deslocamento lateral no beiral (ELS) e flecha vertical na cumeeira.
#   Vento na cobertura aplicado NORMAL a superficie (componentes wx e wy).
#   Gera a memoria de calculo em portugues. Usa frame2d + vento_nbr6123.
# NAO verifica o perfil (isso e feito no check_nbr8800).
# ============================================================================
"""Analise do portico transversal + memoria em PT. Linear elastica, 1a ordem
(2a ordem/B1-B2 e modulo separado). Calcula apenas; pendente revisao."""

from __future__ import annotations

import math
import os

import frame2d as f2d
import vento_nbr6123 as vento

# ---- geometria (portico transversal); plano: x=vao Y, y=altura Z -----------
SPAN = 10.0
EAVE = 6.0
RIDGE = 6.5
BAY = 5.0
THETA = math.atan((RIDGE - EAVE) / (SPAN / 2))   # angulo da agua (5.71 graus)
COS, SIN = math.cos(THETA), math.sin(THETA)
NSEG = 8                                          # sub-divisoes por barra

E = 200e6
A_COL, I_COL = 53.8e-4, 3692e-8   # HEA200
A_RAF, I_RAF = 45.3e-4, 2510e-8   # HEA180

# ---- cargas (kN/m2 de area de telhado; peso proprio kN/m) ------------------
G_ROOF = 0.27          # telha + tercas + suspensas (por area de telhado)
RAFTER_SELF = 0.35     # peso proprio da viga (por metro de barra)
Q_ROOF = 0.25          # sobrecarga (por projecao horizontal)


def _chain(fr, na, nb, Asec, Isec, nseg):
    """Malha nseg barras entre os nos EXISTENTES na e nb (reutiliza os
    extremos, criando so os nos intermediarios). Retorna os indices dos
    elementos."""
    (xa, ya), (xb, yb) = fr.nodes[na], fr.nodes[nb]
    prev = na
    elems = []
    for k in range(1, nseg):
        nk = fr.add_node(xa + (xb - xa) * k / nseg, ya + (yb - ya) * k / nseg)
        elems.append(fr.add_element(prev, nk, E, Asec, Isec))
        prev = nk
    elems.append(fr.add_element(prev, nb, E, Asec, Isec))
    return elems


def _frame():
    fr = f2d.Frame2D()
    # nos de juncao compartilhados
    nBaseL = fr.add_node(0, 0)
    nEaveL = fr.add_node(0, EAVE)
    nRidge = fr.add_node(SPAN / 2, RIDGE)
    nEaveR = fr.add_node(SPAN, EAVE)
    nBaseR = fr.add_node(SPAN, 0)
    eColL = _chain(fr, nBaseL, nEaveL, A_COL, I_COL, NSEG)
    eRafL = _chain(fr, nEaveL, nRidge, A_RAF, I_RAF, NSEG)
    eRafR = _chain(fr, nRidge, nEaveR, A_RAF, I_RAF, NSEG)
    eColR = _chain(fr, nEaveR, nBaseR, A_COL, I_COL, NSEG)
    fr.add_support(nBaseL, u=True, v=True)   # rotulada
    fr.add_support(nBaseR, u=True, v=True)
    ix = dict(colL=eColL, rafL=eRafL, rafR=eRafR, colR=eColR,
              nEaveL=nEaveL, nRidge=nRidge, nEaveR=nEaveR)
    return fr, ix


def _run(load_fn):
    fr, ix = _frame()
    load_fn(fr, ix)
    d, mf = fr.solve()
    return d, mf, ix, fr


# ---- casos de carga --------------------------------------------------------
def case_G(fr, ix):
    # G por area de telhado -> carga vertical por metro de barra = G_ROOF*BAY
    # (SEM cos: a area ja e a real do telhado) + peso proprio da barra.
    wy = -(G_ROOF * BAY + RAFTER_SELF)
    for e in ix["rafL"] + ix["rafR"]:
        fr.add_member_udl(e, wy=wy)


def case_Q(fr, ix):
    # Q por projecao horizontal -> por metro de barra = Q_ROOF*BAY*cos.
    wy = -(Q_ROOF * BAY * COS)
    for e in ix["rafL"] + ix["rafR"]:
        fr.add_member_udl(e, wy=wy)


def _wind(cpi_key):
    r = vento.compute()
    q = r["q_kN_m2"]
    net = r["net"][cpi_key]

    def apply(fr, ix):
        # Paredes: pressao liquida horizontal. Inward = +Y (esq) / -Y (dir).
        for e in ix["colL"]:
            fr.add_member_udl(e, wx=+net["parede_barlavento"] * q * BAY)
        for e in ix["colR"]:
            fr.add_member_udl(e, wx=-net["parede_sotavento"] * q * BAY)
        # Cobertura: pressao NORMAL a agua. n_hat = normal externa (para cima).
        # Carga = -Cp*q*BAY * n_hat  (Cp<0 succao -> sai para fora, +n_hat).
        # agua esquerda (barlavento): normal (-sin, +cos) ; direita (+sin, +cos)
        for e in ix["rafL"]:
            p = net["cobertura_barlavento"] * q * BAY
            fr.add_member_udl(e, wx=-p * (-SIN), wy=-p * COS)
        for e in ix["rafR"]:
            p = net["cobertura_sotavento"] * q * BAY
            fr.add_member_udl(e, wx=-p * (SIN), wy=-p * COS)
    return apply, r


# ---- esforcos ao longo da barra (varre sub-elementos) ----------------------
def _grupo_MNV(mf, elems):
    """Max |M|, |N|, |V| entre os sub-elementos do grupo (le as duas
    extremidades de cada sub-barra -> captura o pico ao longo do vao)."""
    Mm = Nm = Vm = 0.0
    for e in elems:
        f = mf[e]  # [N_i, V_i, M_i, N_j, V_j, M_j]
        Mm = max(Mm, abs(f[2]), abs(f[5]))
        Nm = max(Nm, abs(f[0]), abs(f[3]))
        Vm = max(Vm, abs(f[1]), abs(f[4]))
    return Mm, Nm, Vm


def analyse():
    import numpy as np
    dG, mfG, ix, _ = _run(case_G)
    dQ, mfQ, _, _ = _run(case_Q)
    (w1, wr) = _wind("portao_barlavento")
    dW1, mfW1, _, _ = _run(w1)
    (w2, _) = _wind("portao_sotavento")
    dW2, mfW2, _, _ = _run(w2)

    cases_mf = {"G": mfG, "Q": mfQ, "W1": mfW1, "W2": mfW2}
    cases_d = {"G": dG, "Q": dQ, "W1": dW1, "W2": dW2}

    def combo_mf(c):
        keys = list(mfG.keys())
        return {k: sum(fac * cases_mf[cs][k] for cs, fac in c.items()) for k in keys}

    def combo_d(c):
        v = np.zeros_like(dG)
        for cs, fac in c.items():
            v = v + fac * cases_d[cs]
        return v

    # Combinacoes ELU (NBR 8800). psi0: sobrecarga=0,8 ; vento=0,6.
    combos = {
        "C1_gravidade": {"G": 1.25, "Q": 1.50, "W2": 0.6 * 1.40},
        "C2_uplift": {"G": 1.00, "W1": 1.40},
        "C3_vento_Gdesf": {"G": 1.25, "W2": 1.40, "Q": 0.8 * 1.50},
        "C3_vento_Gfav": {"G": 1.00, "W2": 1.40, "Q": 0.8 * 1.50},
    }
    res = {}
    for name, c in combos.items():
        cmf = combo_mf(c)
        col = max(_grupo_MNV(cmf, ix["colL"]), _grupo_MNV(cmf, ix["colR"]))
        raf = max(_grupo_MNV(cmf, ix["rafL"]), _grupo_MNV(cmf, ix["rafR"]))
        res[name] = {"coluna": col, "viga": raf}

    dser = combo_d({"W2": 1.0})
    drift = abs(dser[3 * ix["nEaveL"]])
    dvert = combo_d({"G": 1.0, "Q": 1.0})
    ridge_v = abs(dvert[3 * ix["nRidge"] + 1])
    return {"wind": wr, "results": res, "drift": drift,
            "drift_lim": EAVE / 300.0, "ridge_v": ridge_v}


def memoria_pt(a):
    L = []
    L += ["=" * 70,
          "MEMORIA DE CALCULO - GALPAO 20x10 m (portico transversal)",
          "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 70, "",
          "1. DADOS",
          "   Vao 10,0 m ; pe-direito 6,0 m ; cumeeira 6,5 m ; inclinacao 10% (5,71 graus)",
          f"   Espacamento de porticos (largura de influencia) = {BAY:.1f} m",
          "   Bases rotuladas. Perfis PLACEHOLDER: colunas HEA200, vigas HEA180.",
          f"   Barras malhadas em {NSEG} trechos (momento avaliado ao longo do vao).",
          "   Analise linear 1a ordem (2a ordem B1/B2 = modulo separado).", "",
          "2. ACOES",
          f"   2.1 Permanente (G): {G_ROOF:.2f} kN/m2 (area de telhado, SEM cos)",
          f"       + peso proprio da viga {RAFTER_SELF:.2f} kN/m",
          f"   2.2 Sobrecarga (Q): {Q_ROOF:.2f} kN/m2 (projecao horizontal, com cos)",
          "   2.3 " + vento.relatorio_pt(a["wind"]).replace("\n", "\n   "),
          "   (Vento na cobertura aplicado NORMAL a superficie: wx e wy)", "",
          "3. COMBINACOES (NBR 8800, ELU) [a confirmar]",
          "   psi0: sobrecarga cobertura = 0,8 ; vento = 0,6",
          "   C1 gravidade:      1,25 G + 1,50 Q + 0,84 W",
          "   C2 uplift:         1,00 G + 1,40 W(portao barlavento)",
          "   C3 vento (G desf): 1,25 G + 1,40 W + 1,20 Q",
          "   C3 vento (G fav):  1,00 G + 1,40 W + 1,20 Q", "",
          "4. ESFORCOS (envoltoria por combinacao) [M kN.m, N kN, V kN]"]
    for name, r in a["results"].items():
        cM, cN, cV = r["coluna"]
        vM, vN, vV = r["viga"]
        L += [f"   {name}:",
              f"     Coluna: M={cM:6.1f}  N={cN:6.1f}  V={cV:6.1f}",
              f"     Viga:   M={vM:6.1f}  N={vN:6.1f}  V={vV:6.1f}"]
    L += ["", "5. DESLOCAMENTOS (ELS)",
          f"   Deslocamento lateral no beiral (vento caract.): {a['drift']*1000:.1f} mm",
          f"     Limite H/300 = {a['drift_lim']*1000:.1f} mm  -> "
          f"{'OK' if a['drift'] <= a['drift_lim'] else 'NAO ATENDE'}",
          f"   Flecha vertical na cumeeira (G+Q): {a['ridge_v']*1000:.1f} mm (verificar L/200)",
          "", "6. OBSERVACOES / PENDENCIAS",
          "   - Coeficientes de vento a confirmar; portao = abertura dominante.",
          "   - Esforcos de 1a ordem: amplificar por B1/B2 (2a ordem) antes do check.",
          "   - Dimensionar/verificar perfis (check_nbr8800), tercas, contravento e bases."]
    import re
    return re.sub(r"(\d)\.(\d)", r"\1,\2", "\n".join(L))


if __name__ == "__main__":
    a = analyse()
    txt = memoria_pt(a)
    print(txt)
    out = "D:/dev/FreeCad_Automatic/projects/galpao/exports"
    os.makedirs(out + "/memoria", exist_ok=True)
    with open(out + "/memoria/memoria-calculo-galpao.txt", "w", encoding="utf-8") as f:
        f.write(txt + "\n")
```

## Resultado da execucao

```
======================================================================
MEMORIA DE CALCULO - GALPAO 20x10 m (portico transversal)
CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL
======================================================================

1. DADOS
   Vao 10,0 m ; pe-direito 6,0 m ; cumeeira 6,5 m ; inclinacao 10% (5,71 graus)
   Espacamento de porticos (largura de influencia) = 5,0 m
   Bases rotuladas. Perfis PLACEHOLDER: colunas HEA200, vigas HEA180.
   Barras malhadas em 8 trechos (momento avaliado ao longo do vao).
   Analise linear 1a ordem (2a ordem B1/B2 = modulo separado).

2. ACOES
   2,1 Permanente (G): 0,27 kN/m2 (area de telhado, SEM cos)
       + peso proprio da viga 0,35 kN/m
   2,2 Sobrecarga (Q): 0,25 kN/m2 (projecao horizontal, com cos)
   2,3 VENTO (ABNT NBR 6123/1988)
     V0 = 40 m/s ; Categoria II ; Classe B
     S1 = 1,00 (topografia plana) ; S3 = 0,95 (galpao deposito)
     S2 = 1,00*0,98*(6,5/10)^0,090 = 0,943
     Vk = 35,82 m/s ; q = 0,613*Vk^2 = 0,787 kN/m2
     Telhado theta = 5,71 graus (10%) ; h/b=0,6 ; a/b=2
     Cpe (Tabela 4 paredes alpha=90 ; Tabela 5 telhado alpha=0):
       parede barlavento: +0,70
       parede sotavento: -0,60
       cobertura barlavento: -0,89
       cobertura sotavento: -0,60
     Cpi (item 6,2.5-c, PORTAO como abertura dominante):
       portao barlavento: +0,80
       portao sotavento: -0,60
     Cp liquido = Cpe - Cpi e pressao (kN/m2):
       caso portao barlavento:
         parede barlavento: -0,10  (-0,079 kN/m2)
         parede sotavento: -1,40  (-1,102 kN/m2)
         cobertura barlavento: -1,69  (-1,330 kN/m2)
         cobertura sotavento: -1,40  (-1,102 kN/m2)
       caso portao sotavento:
         parede barlavento: +1,30  (+1,023 kN/m2)
         parede sotavento: +0,00  (+0,000 kN/m2)
         cobertura barlavento: -0,29  (-0,228 kN/m2)
         cobertura sotavento: +0,00  (+0,000 kN/m2)
     [A CONFIRMAR: classe (20 m), S3=0,95, mapeamento de zonas/alpha e
      razao de areas das aberturas para o Cpi do portao (6,2.5-c).]
   (Vento na cobertura aplicado NORMAL a superficie: wx e wy)

3. COMBINACOES (NBR 8800, ELU) [a confirmar]
   psi0: sobrecarga cobertura = 0,8 ; vento = 0,6
   C1 gravidade:      1,25 G + 1,50 Q + 0,84 W
   C2 uplift:         1,00 G + 1,40 W(portao barlavento)
   C3 vento (G desf): 1,25 G + 1,40 W + 1,20 Q
   C3 vento (G fav):  1,00 G + 1,40 W + 1,20 Q

4. ESFORCOS (envoltoria por combinacao) [M kN.m, N kN, V kN]
   C1_gravidade:
     Coluna: M=  60,7  N=  26,3  V=  10,1
     Viga:   M=  60,7  N=  12,7  V=  25,2
   C2_uplift:
     Coluna: M= 107,0  N=  48,4  V=  19,5
     Viga:   M= 107,0  N=  25,1  V=  46,2
   C3_vento_Gdesf:
     Coluna: M=  81,5  N=  28,6  V=  13,6
     Viga:   M=  81,5  N=  16,4  V=  27,1
   C3_vento_Gfav:
     Coluna: M=  78,8  N=  26,4  V=  13,1
     Viga:   M=  78,8  N=  15,7  V=  25,0

5. DESLOCAMENTOS (ELS)
   Deslocamento lateral no beiral (vento caract.): 177,3 mm
     Limite H/300 = 20,0 mm  -> NAO ATENDE
   Flecha vertical na cumeeira (G+Q): 26,7 mm (verificar L/200)

6. OBSERVACOES / PENDENCIAS
   - Coeficientes de vento a confirmar; portao = abertura dominante.
   - Esforcos de 1a ordem: amplificar por B1/B2 (2a ordem) antes do check.
   - Dimensionar/verificar perfis (check_nbr8800), tercas, contravento e bases.
```
