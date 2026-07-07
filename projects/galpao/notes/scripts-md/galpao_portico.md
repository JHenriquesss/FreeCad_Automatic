# Portico transversal - galpao_portico.py

Arquivo: `framework/galpao_fw/galpao_portico.py`  
Gerado: 2026-07-06  
Status: APROVADO pelo eng. senior (1a ordem + PONTE). ATUALIZADO 2026-07-06: combinacoes ELU agora sao ENVELOPE - cada hipotese de gravidade cruza W1 e W2 (_combos_elu), diretriz do senior. Referencia craneless INALTERADA (col 0,67 / viga 0,93; so os rotulos dos combos mudaram). Guardado por PONTE=None.

## Codigo completo

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
BASE_FIXED = False                # False = base rotulada ; True = engastada

# ---- cargas (kN/m2 de area de telhado; peso proprio kN/m) ------------------
G_ROOF = 0.27          # telha + tercas + suspensas (por area de telhado)
RAFTER_SELF = 0.35     # peso proprio da viga (por metro de barra)
Q_ROOF = 0.25          # sobrecarga (por projecao horizontal)

# ---- ponte rolante (opcional). None = galpao SEM ponte (nao altera nada). ----
# dict do ponte_rolante.reacao_no_portico + altura do trilho:
#   {"R_vert","M_exc","H_transv","Hvr"} (kN, kN.m, kN, m).
PONTE = None


def configurar(span=None, eave=None, ridge=None, bay=None, base_fixed=None,
               A_col=None, I_col=None, A_raf=None, I_raf=None,
               G_roof=None, rafter_self=None, Q_roof=None, ponte=None):
    """Define a geometria/cargas do projeto (do gate) e RECOMPUTA os derivados.
    Nao altera o metodo de calculo - so troca os dados de entrada. Chamar antes
    de analyse(). Argumentos None mantem o valor atual."""
    global SPAN, EAVE, RIDGE, BAY, THETA, COS, SIN, BASE_FIXED
    global A_COL, I_COL, A_RAF, I_RAF, G_ROOF, RAFTER_SELF, Q_ROOF, PONTE
    if ponte is not None: PONTE = ponte if ponte else None
    if span is not None:  SPAN = float(span)
    if eave is not None:  EAVE = float(eave)
    if ridge is not None: RIDGE = float(ridge)
    if bay is not None:   BAY = float(bay)
    if base_fixed is not None: BASE_FIXED = bool(base_fixed)
    if A_col is not None: A_COL = A_col
    if I_col is not None: I_COL = I_col
    if A_raf is not None: A_RAF = A_raf
    if I_raf is not None: I_RAF = I_raf
    if G_roof is not None: G_ROOF = G_roof
    if rafter_self is not None: RAFTER_SELF = rafter_self
    if Q_roof is not None: Q_ROOF = Q_roof
    THETA = math.atan((RIDGE - EAVE) / (SPAN / 2))
    COS, SIN = math.cos(THETA), math.sin(THETA)


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
    nConsL = None
    if PONTE:                                    # no do console no nivel do trilho
        nConsL = fr.add_node(0, float(PONTE["Hvr"]))
        eColL = (_chain(fr, nBaseL, nConsL, A_COL, I_COL, max(2, NSEG // 2)) +
                 _chain(fr, nConsL, nEaveL, A_COL, I_COL, max(2, NSEG // 2)))
    else:
        eColL = _chain(fr, nBaseL, nEaveL, A_COL, I_COL, NSEG)
    eRafL = _chain(fr, nEaveL, nRidge, A_RAF, I_RAF, NSEG)
    eRafR = _chain(fr, nRidge, nEaveR, A_RAF, I_RAF, NSEG)
    eColR = _chain(fr, nEaveR, nBaseR, A_COL, I_COL, NSEG)
    fr.add_support(nBaseL, u=True, v=True, rot=BASE_FIXED)   # rotulada/engastada
    fr.add_support(nBaseR, u=True, v=True, rot=BASE_FIXED)
    ix = dict(colL=eColL, rafL=eRafL, rafR=eRafR, colR=eColR,
              nEaveL=nEaveL, nRidge=nRidge, nEaveR=nEaveR,
              nBaseL=nBaseL, nBaseR=nBaseR, nConsL=nConsL)
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


def case_ponte(fr, ix):
    """Reacao da ponte no console (nivel do trilho): vertical R_vert, momento
    EXCENTRICO concentrado (trilho fora do eixo do pilar) e surto transversal.
    So a coluna esquerda (governante; portico simetrico). Diretriz do senior:
    o M_excentrico costuma governar a coluna inferior."""
    p = PONTE
    n = ix["nConsL"]
    fr.add_nodal_load(n, Fy=-abs(p["R_vert"]), M=p["M_exc"], Fx=abs(p["H_transv"]))


def _combos_elu(ponte=None):
    """Combinacoes ELU (NBR 8800) - ENVELOPE: cada hipotese de gravidade cruzada
    com CADA caso de vento (W1=portao barlavento, W2=portao sotavento). Antes o
    vento era fixado por combo (W2 na C1/C3, W1 na C2); o cruzamento pega o pior
    (diretriz do senior). psi0: sobrecarga=0,8 ; vento=0,6. Q FAVORAVEL no uplift
    (G=1,00) nao entra."""
    combos = {}
    for wc in ("W1", "W2"):
        combos[f"C1_grav_{wc}"] = {"G": 1.25, "Q": 1.50, wc: 0.6 * 1.40}
        combos[f"C2_uplift_{wc}"] = {"G": 1.00, wc: 1.40}            # sem Q (favor.)
        combos[f"C3_Gdesf_{wc}"] = {"G": 1.25, wc: 1.40, "Q": 0.8 * 1.50}
        combos[f"C3_Gfav_{wc}"] = {"G": 1.00, wc: 1.40}             # sem Q (favor.)
        if ponte:
            # Ponte = acao variavel autonoma (diretriz do senior).
            combos[f"C4_ponte_{wc}"] = {"G": 1.25, "PONTE": 1.50, wc: 0.6 * 1.40, "Q": 0.8 * 1.50}
            combos[f"C5_vento_ponte_{wc}"] = {"G": 1.25, wc: 1.40, "PONTE": 0.7 * 1.50, "Q": 0.8 * 1.50}
    return combos


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
    if PONTE:
        dP, mfP, _, _ = _run(case_ponte)
        cases_mf["PONTE"] = mfP; cases_d["PONTE"] = dP

    def combo_mf(c):
        keys = list(mfG.keys())
        return {k: sum(fac * cases_mf[cs][k] for cs, fac in c.items()) for k in keys}

    def combo_d(c):
        v = np.zeros_like(dG)
        for cs, fac in c.items():
            v = v + fac * cases_d[cs]
        return v

    # Combinacoes ELU (NBR 8800). psi0: sobrecarga=0,8 ; vento=0,6.
    # REGRA: acoes variaveis FAVORAVEIS entram com gamma=0 (nao se somam).
    # Nas combinacoes de UPLIFT (G favoravel, gamma_g=1,00), a sobrecarga Q
    # atua para BAIXO -> resiste ao levantamento -> e FAVORAVEL -> Q NAO entra.
    combos = _combos_elu(PONTE)
    res = {}
    for name, c in combos.items():
        cmf = combo_mf(c)
        col = max(_grupo_MNV(cmf, ix["colL"]), _grupo_MNV(cmf, ix["colR"]))
        raf = max(_grupo_MNV(cmf, ix["rafL"]), _grupo_MNV(cmf, ix["rafR"]))
        res[name] = {"coluna": col, "viga": raf}

    # ELS: vento caracteristico (sem majoracao). Toma o maior deslocamento
    # lateral entre os dois casos de vento e os dois beirais.
    drift = 0.0
    for cs in ("W1", "W2"):
        dv = combo_d({cs: 1.0})
        drift = max(drift, abs(dv[3 * ix["nEaveL"]]), abs(dv[3 * ix["nEaveR"]]))
    dvert = combo_d({"G": 1.0, "Q": 1.0})
    ridge_v = abs(dvert[3 * ix["nRidge"] + 1])
    # Limites de deslocamento lateral (NBR 8800, Anexo C). H/300 e para porticos
    # que suportam ALVENARIA; para galpao com fechamento em TELHA METALICA
    # (sem elementos frageis) admite-se H/200 ou H/150 (Bellei, Anexo C nota).
    lims = {"H/300": EAVE / 300.0, "H/250": EAVE / 250.0,
            "H/200": EAVE / 200.0, "H/150": EAVE / 150.0}
    return {"wind": wr, "results": res, "drift": drift,
            "drift_lims": lims, "drift_ref": "H/150", "ridge_v": ridge_v}


def memoria_pt(a):
    L = []
    L += ["=" * 70,
          "MEMORIA DE CALCULO - GALPAO 20x10 m (portico transversal)",
          "CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO RESPONSAVEL", "=" * 70, "",
          "1. DADOS",
          "   Vao 10,0 m ; pe-direito 6,0 m ; cumeeira 6,5 m ; inclinacao 10% (5,71 graus)",
          f"   Espacamento de porticos (largura de influencia) = {BAY:.1f} m",
          f"   Bases {'ENGASTADAS' if BASE_FIXED else 'rotuladas'}. "
          "Perfis: colunas HEA200, vigas HEA180.",
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
          "   Regra: acao variavel FAVORAVEL entra com gamma = 0 (nao se soma).",
          "   C1 gravidade:      1,25 G + 1,50 Q + 0,84 W",
          "   C2 uplift:         1,00 G + 1,40 W(portao barlavento)   [Q=0 favor.]",
          "   C3 vento (G desf): 1,25 G + 1,40 W + 1,20 Q",
          "   C3 vento (G fav):  1,00 G + 1,40 W                       [Q=0 favor.]", "",
          "4. ESFORCOS (envoltoria por combinacao) [M kN.m, N kN, V kN]"]
    for name, r in a["results"].items():
        cM, cN, cV = r["coluna"]
        vM, vN, vV = r["viga"]
        L += [f"   {name}:",
              f"     Coluna: M={cM:6.1f}  N={cN:6.1f}  V={cV:6.1f}",
              f"     Viga:   M={vM:6.1f}  N={vN:6.1f}  V={vV:6.1f}"]
    L += ["", "5. DESLOCAMENTOS (ELS) - vento caracteristico (sem majoracao)",
          f"   Deslocamento lateral no beiral: {a['drift']*1000:.1f} mm",
          "     Limites NBR 8800 Anexo C (H/300 = alvenaria ; telha metalica"
          " admite ate H/150):"]
    for nome, lim in a["drift_lims"].items():
        ok = "OK" if a["drift"] <= lim else "NAO ATENDE"
        marca = "   <== referencia (telha metalica, sem alvenaria)" \
            if nome == a["drift_ref"] else ""
        L += [f"       {nome} = {lim*1000:5.1f} mm  -> {ok}{marca}"]
    L += [f"   Flecha vertical na cumeeira (G+Q): {a['ridge_v']*1000:.1f} mm (verificar L/250)",
          "", "6. OBSERVACOES / PENDENCIAS",
          "   - Coeficientes de vento a confirmar; portao = abertura dominante.",
          "   - Esforcos de 1a ordem: amplificar por B1/B2 (2a ordem) antes do check.",
          "   - Dimensionar/verificar perfis (check_nbr8800), tercas, contravento e bases."]
    import re
    # virgula decimal (PT) sem mastigar numeros de clausula (ex.: 6.2.5-c).
    return re.sub(r"(?<!\d\.)(\d)\.(\d)(?!\.\d)", r"\1,\2", "\n".join(L))


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
   Bases rotuladas. Perfis: colunas HEA200, vigas HEA180.
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
     Cpe (MESMA incidencia alpha=90: paredes Tab.4 A/B ; telhado Tab.5 EF/GH):
       parede barlavento: +0,70
       parede sotavento: -0,60
       cobertura barlavento: -0,93
       cobertura sotavento: -0,60
     Cpi (item 6.2.5-c, PORTAO como abertura dominante):
       portao barlavento: +0,80
       portao sotavento: -0,60
     Cp liquido = Cpe - Cpi e pressao (kN/m2):
       caso portao barlavento:
         parede barlavento: -0,10  (-0,079 kN/m2)
         parede sotavento: -1,40  (-1,102 kN/m2)
         cobertura barlavento: -1,73  (-1,362 kN/m2)
         cobertura sotavento: -1,40  (-1,102 kN/m2)
       caso portao sotavento:
         parede barlavento: +1,30  (+1,023 kN/m2)
         parede sotavento: +0,00  (+0,000 kN/m2)
         cobertura barlavento: -0,33  (-0,260 kN/m2)
         cobertura sotavento: +0,00  (+0,000 kN/m2)
     [A CONFIRMAR: classe (20 m), S3=0,95, mapeamento de zonas/alpha e
      razao de areas das aberturas para o Cpi do portao (6.2.5-c).]
   (Vento na cobertura aplicado NORMAL a superficie: wx e wy)

3. COMBINACOES (NBR 8800, ELU) [a confirmar]
   psi0: sobrecarga cobertura = 0,8 ; vento = 0,6
   Regra: acao variavel FAVORAVEL entra com gamma = 0 (nao se soma).
   C1 gravidade:      1,25 G + 1,50 Q + 0,84 W
   C2 uplift:         1,00 G + 1,40 W(portao barlavento)   [Q=0 favor.]
   C3 vento (G desf): 1,25 G + 1,40 W + 1,20 Q
   C3 vento (G fav):  1,00 G + 1,40 W                       [Q=0 favor.]

4. ESFORCOS (envoltoria por combinacao) [M kN.m, N kN, V kN]
   C1_grav_W1:
     Coluna: M=  45,2  N=  14,6  V=   8,5
     Viga:   M=  45,2  N=  11,9  V=  13,6
   C2_uplift_W1:
     Coluna: M= 107,4  N=  49,2  V=  19,6
     Viga:   M= 107,4  N=  25,2  V=  47,0
   C3_Gdesf_W1:
     Coluna: M=  95,0  N=  39,5  V=  17,5
     Viga:   M=  95,0  N=  23,1  V=  37,6
   C3_Gfav_W1:
     Coluna: M= 107,4  N=  49,2  V=  19,6
     Viga:   M= 107,4  N=  25,2  V=  47,0
   C1_grav_W2:
     Coluna: M=  60,1  N=  26,1  V=  10,0
     Viga:   M=  60,1  N=  12,6  V=  25,0
   C2_uplift_W2:
     Coluna: M=  68,0  N=  18,6  V=  11,3
     Viga:   M=  68,0  N=  13,1  V=  17,4
   C3_Gdesf_W2:
     Coluna: M=  80,5  N=  28,2  V=  13,4
     Viga:   M=  80,5  N=  16,2  V=  26,8
   C3_Gfav_W2:
     Coluna: M=  68,0  N=  18,6  V=  11,3
     Viga:   M=  68,0  N=  13,1  V=  17,4

5. DESLOCAMENTOS (ELS) - vento caracteristico (sem majoracao)
   Deslocamento lateral no beiral: 179,0 mm
     Limites NBR 8800 Anexo C (H/300 = alvenaria ; telha metalica admite ate H/150):
       H/300 =  20,0 mm  -> NAO ATENDE
       H/250 =  24,0 mm  -> NAO ATENDE
       H/200 =  30,0 mm  -> NAO ATENDE
       H/150 =  40,0 mm  -> NAO ATENDE   <== referencia (telha metalica, sem alvenaria)
   Flecha vertical na cumeeira (G+Q): 26,7 mm (verificar L/250)

6. OBSERVACOES / PENDENCIAS
   - Coeficientes de vento a confirmar; portao = abertura dominante.
   - Esforcos de 1a ordem: amplificar por B1/B2 (2a ordem) antes do check.
   - Dimensionar/verificar perfis (check_nbr8800), tercas, contravento e bases.
```
