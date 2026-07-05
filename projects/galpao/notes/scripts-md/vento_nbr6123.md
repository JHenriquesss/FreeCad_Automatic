# vento_nbr6123.py

Vento NBR 6123 - S2, Vk, q, Cpe (Tabelas 4 e 5), Cpi (item 6.2.5-c, portao dominante).

CONCEITUAL - PENDENTE REVISAO DO ENGENHEIRO. Codigo em ingles; saidas em PT.

## Codigo

```python
"""Wind loads per ABNT NBR 6123/1988 for the galpao transverse frame.

Coefficients are the ACTUAL table values (Tabela 1, 4, 5 and item 6.2), read from
the standard, with clause references. Transparent and auditable. The zone/alpha
mapping and the dominant-opening area ratio are flagged for engineer confirmation.
Outputs in Portuguese. Computes only; pending engineer review. Units: m, kN.

Building: a=20 (length), b=10 (span/width), h=6 (eave). h/b=0.6 ; a/b=2.
Transverse frame = wind perpendicular to the ridge (hits the long 20 m walls).
"""

from __future__ import annotations


def s2_factor(cat, classe, z):
    """NBR 6123 Tabela 1 (categoria II)."""
    tbl = {
        ("II", "A"): (1.00, 1.00, 0.085),
        ("II", "B"): (1.00, 0.98, 0.09),
        ("II", "C"): (1.00, 0.95, 0.10),
    }
    b, Fr, p = tbl[(cat, classe)]
    return b, Fr, p, b * Fr * (z / 10.0) ** p


def _interp(x, x0, x1, y0, y1):
    return y0 + (x - x0) / (x1 - x0) * (y1 - y0)


def cpe_paredes():
    """NBR 6123 Tabela 4, paredes. Vento transversal atinge as paredes longas
    (a=20). Bloco 1/2<h/b<=3/2, linha 2<=a/b<=4, incidencia alpha=90 (faces A,B).
    A = barlavento, B = sotavento."""
    return {"parede_barlavento": +0.70, "parede_sotavento": -0.60}


def cpe_telhado(theta_graus=5.71):
    """NBR 6123 Tabela 5, telhado duas aguas. Bloco 1/2<h/b<=3/2, alpha=0
    (vento perpendicular a cumeeira). Colunas EG (agua barlavento) e FH (agua
    sotavento). Interpola theta entre 5 e 10 graus.
    5 graus:  EG=-0,9  FH=-0,6 ; 10 graus: EG=-0,8  FH=-0,6."""
    eg = _interp(theta_graus, 5.0, 10.0, -0.9, -0.8)
    fh = _interp(theta_graus, 5.0, 10.0, -0.6, -0.6)
    return {"cobertura_barlavento": round(eg, 2), "cobertura_sotavento": round(fh, 2)}


def cpi_cases():
    """NBR 6123 item 6.2.5-c: PORTAO = abertura dominante no oitao.
    - Portao a barlavento (vento no oitao): Cpi = +0,1 a +0,8 conforme a razao
      (area do portao / area das demais aberturas sob succao). Adotado +0,8
      (conservador, razao >=6) - A CONFIRMAR com a razao real das aberturas.
    - Portao a sotavento: Cpi = Cpe da face de sotavento (Tabela 4) = -0,6.
    Consideram-se ambos; o engenheiro escolhe/refina."""
    return {"portao_barlavento": +0.80, "portao_sotavento": -0.60}


def compute(v0=40.0, cat="II", classe="B", s1=1.0, s3=0.95, z=6.5, theta=5.71):
    b, Fr, p, s2 = s2_factor(cat, classe, z)
    vk = v0 * s1 * s2 * s3
    q = 0.613 * vk ** 2 / 1000.0
    cpe = {**cpe_paredes(), **cpe_telhado(theta)}
    cpi = cpi_cases()
    net = {}
    for cname, cpiv in cpi.items():
        net[cname] = {s: round(cpe[s] - cpiv, 2) for s in cpe}
    return {"v0": v0, "cat": cat, "classe": classe, "s1": s1, "s2": round(s2, 3),
            "s3": s3, "Fr": Fr, "p": p, "z": z, "theta": theta,
            "vk": round(vk, 2), "q_kN_m2": round(q, 3),
            "cpe": cpe, "cpi_cases": cpi, "net": net}


def relatorio_pt(r):
    L = []
    L.append("VENTO (ABNT NBR 6123/1988)")
    L.append(f"  V0 = {r['v0']:.0f} m/s ; Categoria {r['cat']} ; Classe {r['classe']}")
    L.append(f"  S1 = {r['s1']:.2f} (topografia plana) ; S3 = {r['s3']:.2f} (galpao deposito)")
    L.append(f"  S2 = 1,00*{r['Fr']:.2f}*({r['z']:.1f}/10)^{r['p']:.3f} = {r['s2']:.3f}")
    L.append(f"  Vk = {r['vk']:.2f} m/s ; q = 0,613*Vk^2 = {r['q_kN_m2']:.3f} kN/m2")
    L.append(f"  Telhado theta = {r['theta']:.2f} graus (10%) ; h/b=0,6 ; a/b=2")
    L.append("  Cpe (Tabela 4 paredes alpha=90 ; Tabela 5 telhado alpha=0):")
    for s, v in r["cpe"].items():
        L.append(f"    {s.replace('_',' ')}: {v:+.2f}")
    L.append("  Cpi (item 6.2.5-c, PORTAO como abertura dominante):")
    for k, v in r["cpi_cases"].items():
        L.append(f"    {k.replace('_',' ')}: {v:+.2f}")
    L.append("  Cp liquido = Cpe - Cpi e pressao (kN/m2):")
    for caso, d in r["net"].items():
        L.append(f"    caso {caso.replace('_',' ')}:")
        for s, v in d.items():
            L.append(f"      {s.replace('_',' ')}: {v:+.2f}  ({v*r['q_kN_m2']:+.3f} kN/m2)")
    L.append("  [A CONFIRMAR: classe (20 m), S3=0,95, mapeamento de zonas/alpha e")
    L.append("   razao de areas das aberturas para o Cpi do portao (6.2.5-c).]")
    return "\n".join(L)


if __name__ == "__main__":
    print(relatorio_pt(compute()))
```

## Resultado da execucao

```
VENTO (ABNT NBR 6123/1988)
  V0 = 40 m/s ; Categoria II ; Classe B
  S1 = 1.00 (topografia plana) ; S3 = 0.95 (galpao deposito)
  S2 = 1,00*0.98*(6.5/10)^0.090 = 0.943
  Vk = 35.82 m/s ; q = 0,613*Vk^2 = 0.787 kN/m2
  Telhado theta = 5.71 graus (10%) ; h/b=0,6 ; a/b=2
  Cpe (Tabela 4 paredes alpha=90 ; Tabela 5 telhado alpha=0):
    parede barlavento: +0.70
    parede sotavento: -0.60
    cobertura barlavento: -0.89
    cobertura sotavento: -0.60
  Cpi (item 6.2.5-c, PORTAO como abertura dominante):
    portao barlavento: +0.80
    portao sotavento: -0.60
  Cp liquido = Cpe - Cpi e pressao (kN/m2):
    caso portao barlavento:
      parede barlavento: -0.10  (-0.079 kN/m2)
      parede sotavento: -1.40  (-1.102 kN/m2)
      cobertura barlavento: -1.69  (-1.330 kN/m2)
      cobertura sotavento: -1.40  (-1.102 kN/m2)
    caso portao sotavento:
      parede barlavento: +1.30  (+1.023 kN/m2)
      parede sotavento: +0.00  (+0.000 kN/m2)
      cobertura barlavento: -0.29  (-0.228 kN/m2)
      cobertura sotavento: +0.00  (+0.000 kN/m2)
  [A CONFIRMAR: classe (20 m), S3=0,95, mapeamento de zonas/alpha e
   razao de areas das aberturas para o Cpi do portao (6.2.5-c).]
```
