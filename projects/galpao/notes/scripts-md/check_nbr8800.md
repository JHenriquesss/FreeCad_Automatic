# check_nbr8800.py

Verificacao de perfil NBR 8800 - tracao, compressao, flexao/FLT, cortante, interacao 5.5.1.2.

CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO. Codigo em ingles; saidas em PT.

## Codigo

```python
# ============================================================================
# check_nbr8800.py - O QUE ESTE SCRIPT FAZ / CALCULA
# Verifica um perfil metalico pela ABNT NBR 8800:2008 dados os esforcos
# solicitantes (Nsd, Msd, Vsd).
#   Calcula as resistencias de calculo: tracao (5.2), compressao com flambagem
#   global (5.3, fator chi da Tabela 4), flexao com FLT (5.4/Anexo G,
#   simplificado), cortante (5.4.3).
#   Calcula: razoes de utilizacao (N/Nrd, M/Mrd, V/Vrd) e a interacao
#   flexo-compressao (5.5.1.2), com veredito passa / nao passa.
# NAO calcula esforcos (vem do galpao_portico) - so verifica a secao.
# ============================================================================
"""Verificacao de perfil metalico conforme ABNT NBR 8800:2008.

Recebe propriedades da secao + esforcos solicitantes (Nsd, Msd, Vsd) e calcula as
resistencias de calculo e as razoes de utilizacao. Transparente e auditavel, com
as clausulas citadas. Calcula apenas; pendente revisao do engenheiro.

Verifica: tracao (5.2), compressao com flambagem global (5.3, chi da Tabela 4),
flexao com FLT (5.4/Anexo G, simplificado), cortante (5.4.3) e a interacao
flexo-compressao (5.5.1.2). Flambagem local: Q=1 assumido (secao compacta) - a
confirmar. Unidades internas: kN, m, kN/m2.
"""

from __future__ import annotations

import math

E = 200e6          # kN/m2 (200 GPa)
GA1 = 1.10         # coef. de resistencia ao escoamento/flambagem
GA2 = 1.35         # coef. de resistencia a ruptura


def chi_compressao(lambda0):
    """NBR 8800 5.3.3 / Tabela 4: fator de reducao chi."""
    if lambda0 <= 1.5:
        return 0.658 ** (lambda0 ** 2)
    return 0.877 / lambda0 ** 2


def verifica(sec, fy, L, Nsd, Msd, Vsd, Kx=1.0, Ky=1.0, Lb=None, Q=1.0, Cb=1.0,
             nome=""):
    """sec: dict com A, Ix, Iy, ry, Zx, Wx, Aw (SI: m2, m4, m, m3).
    fy em kN/m2. L, Lb em m. Retorna dict de resultados."""
    A, Ix, Iy = sec["A"], sec["Ix"], sec["Iy"]
    ry, Zx, Wx, Aw = sec["ry"], sec["Zx"], sec["Wx"], sec["Aw"]
    if Lb is None:
        Lb = L
    r = {"nome": nome}

    # --- Tracao (5.2): escoamento da secao bruta ---
    Nt_Rd = A * fy / GA1
    r["Nt_Rd"] = Nt_Rd

    # --- Compressao (5.3): flambagem global, dois eixos ---
    Ne_x = math.pi ** 2 * E * Ix / (Kx * L) ** 2
    Ne_y = math.pi ** 2 * E * Iy / (Ky * Lb) ** 2
    Ne = min(Ne_x, Ne_y)
    lambda0 = math.sqrt(Q * A * fy / Ne)
    chi = chi_compressao(lambda0)
    Nc_Rd = chi * Q * A * fy / GA1
    r.update(Ne=Ne, lambda0=lambda0, chi=chi, Nc_Rd=Nc_Rd)

    # --- Flexao com FLT (5.4 / Anexo G), eixo forte, simplificado ---
    Mpl = Zx * fy
    Lp = 1.76 * ry * math.sqrt(E / fy)
    if Lb <= Lp:
        Mn = Mpl
        flt = "sem FLT (Lb<=Lp): Mn=Mpl"
    else:
        # Mr = fy*Wx (inicio do regime inelastico, conservador sem residual);
        # Lr aproximado por pi*ry*sqrt(E/(0.7fy)) (limite elastico simplificado).
        Mr = fy * Wx
        Lr = math.pi * ry * math.sqrt(E / (0.7 * fy))
        if Lb <= Lr:
            Mn = min(Cb * (Mpl - (Mpl - Mr) * (Lb - Lp) / (Lr - Lp)), Mpl)
            flt = "FLT inelastica (Lp<Lb<=Lr) - VERIFICAR Anexo G detalhado"
        else:
            Mcr = Cb * math.pi ** 2 * E * Iy / Lb ** 2  # simplificado (só termo empenamento omitido)
            Mn = min(Mcr, Mpl)
            flt = "FLT elastica (Lb>Lr) - VERIFICAR Anexo G detalhado"
    Mrd = Mn / GA1
    r.update(Mpl=Mpl, Lp=Lp, Lb=Lb, Mn=Mn, Mrd=Mrd, flt=flt)

    # --- Cortante (5.4.3), alma compacta ---
    Vpl = 0.6 * Aw * fy
    Vrd = Vpl / GA1
    r["Vrd"] = Vrd

    # --- Razoes de utilizacao ---
    r["u_N_trac"] = Nsd / Nt_Rd if Nsd > 0 else 0.0
    r["u_N_comp"] = Nsd / Nc_Rd
    r["u_M"] = Msd / Mrd
    r["u_V"] = Vsd / Vrd

    # --- Interacao flexo-compressao (5.5.1.2) ---
    n = Nsd / Nc_Rd
    m = Msd / Mrd
    if n >= 0.2:
        inter = n + (8.0 / 9.0) * m
        eq = "N/Nrd + 8/9*(M/Mrd)"
    else:
        inter = n / 2.0 + m
        eq = "N/(2Nrd) + M/Mrd"
    r.update(interacao=inter, eq_interacao=eq)
    r["OK"] = (inter <= 1.0 and r["u_V"] <= 1.0)
    return r


def relatorio_pt(rs, fy):
    L = []
    L.append("VERIFICACAO DE PERFIS (ABNT NBR 8800:2008)")
    L.append(f"  fy = {fy/1000:.0f} MPa ; gamma_a1 = {GA1:.2f} ; Q = 1,0 (compacta, a confirmar)")
    for r in rs:
        L.append("")
        L.append(f"  --- {r['nome']} ---")
        L.append(f"  Compressao: Ne={r['Ne']:.0f} kN ; lambda0={r['lambda0']:.3f} ; "
                 f"chi={r['chi']:.3f} ; Nc,Rd={r['Nc_Rd']:.1f} kN")
        L.append(f"  Flexao: Mpl={r['Mpl']:.1f} ; Lp={r['Lp']:.2f} m ; Lb={r['Lb']:.2f} m ; "
                 f"Mrd={r['Mrd']:.1f} kN.m ({r['flt']})")
        L.append(f"  Cortante: Vrd={r['Vrd']:.1f} kN")
        L.append(f"  Utilizacao: N/Nc={r['u_N_comp']:.2f} ; M/Mrd={r['u_M']:.2f} ; "
                 f"V/Vrd={r['u_V']:.2f}")
        L.append(f"  Interacao ({r['eq_interacao']}) = {r['interacao']:.2f}  -> "
                 f"{'OK' if r['OK'] else 'NAO PASSA'}")
    import re
    return re.sub(r"(\d)\.(\d)", r"\1,\2", "\n".join(L))


# ---- secoes (SI: m2, m4, m, m3) --------------------------------------------
HEA200 = {"A": 53.83e-4, "Ix": 3692e-8, "Iy": 1336e-8, "ry": 0.0498,
          "Zx": 429.5e-6, "Wx": 388.6e-6, "Aw": 0.190 * 0.0065}
HEA180 = {"A": 45.25e-4, "Ix": 2510e-8, "Iy": 924.6e-8, "ry": 0.0452,
          "Zx": 324.9e-6, "Wx": 293.6e-6, "Aw": 0.171 * 0.006}


if __name__ == "__main__":
    fy = 250e3  # kN/m2 (aco MR250 / ASTM A36)
    # Esforcos da combinacao governante C2 (galpao_portico): coluna e viga.
    col = verifica(HEA200, fy, L=6.0, Nsd=48.9, Msd=109.8, Vsd=19.9,
                   Kx=2.0, Ky=1.0, Lb=2.0, nome="Coluna HEA200 (K x=2 sway; Lb=2 m girts)")
    raf = verifica(HEA180, fy, L=5.03, Nsd=24.7, Msd=109.8, Vsd=46.7,
                   Kx=1.0, Ky=1.0, Lb=1.67, nome="Viga HEA180 (Lb=1,67 m tercas)")
    print(relatorio_pt([col, raf], fy))
```

## Resultado da execucao

```
VERIFICACAO DE PERFIS (ABNT NBR 8800:2008)
  fy = 250 MPa ; gamma_a1 = 1,10 ; Q = 1,0 (compacta, a confirmar)

  --- Coluna HEA200 (K x=2 sway; Lb=2 m girts) ---
  Compressao: Ne=506 kN ; lambda0=1,631 ; chi=0,330 ; Nc,Rd=403,5 kN
  Flexao: Mpl=107,4 ; Lp=2,48 m ; Lb=2,00 m ; Mrd=97,6 kN.m (sem FLT (Lb<=Lp): Mn=Mpl)
  Cortante: Vrd=168,4 kN
  Utilizacao: N/Nc=0,12 ; M/Mrd=1,12 ; V/Vrd=0,12
  Interacao (N/(2Nrd) + M/Mrd) = 1,19  -> NAO PASSA

  --- Viga HEA180 (Lb=1,67 m tercas) ---
  Compressao: Ne=1958 kN ; lambda0=0,760 ; chi=0,785 ; Nc,Rd=807,5 kN
  Flexao: Mpl=81,2 ; Lp=2,25 m ; Lb=1,67 m ; Mrd=73,8 kN.m (sem FLT (Lb<=Lp): Mn=Mpl)
  Cortante: Vrd=139,9 kN
  Utilizacao: N/Nc=0,03 ; M/Mrd=1,49 ; V/Vrd=0,33
  Interacao (N/(2Nrd) + M/Mrd) = 1,50  -> NAO PASSA
```
