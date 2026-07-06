# Revisão — Ponte rolante + viga de rolamento

Conferência do sênior. Ação de ponte rolante pela **NBR 8800:2008** (+ NBR 8400
para classes/impacto): cargas verticais/transversais/longitudinais, viga de
rolamento e a reação empacotada para o pórtico (console/pilar).

Código: `ponte_rolante.py` (reusa `check_nbr8800`). Referência do método:
"Dimensionamento de elementos estruturais de aço e mistos" (cap. 4) + NBR 8800.
Última atualização: 2026-07-06.

> φ (impacto), frac_lateral, frac_long = **fabricante / NBR 8400 (A CONFIRMAR)** —
> não inventados; entram flagados.

---

## 1. Cargas de roda (Rmax/Rmin)

Ponte encostada, trole na aproximação mínima `a` de um trilho:

```python
def cargas_de_roda(Q, peso_ponte, peso_trole, vao_ponte, aprox_min, n_rodas_lado):
    S = vao_ponte
    movel = Q + peso_trole
    R_trilho_max = peso_ponte / 2.0 + movel * (S - aprox_min) / S
    R_trilho_min = peso_ponte / 2.0 + movel * aprox_min / S
    return (R_trilho_max / n_rodas_lado, R_trilho_min / n_rodas_lado,
            R_trilho_max, R_trilho_min)
```

Vertical majorado por **φ** (impacto, 1,10 leve … 1,25 pesada/siderúrgica).

---

## 2. Forças horizontais

```python
def forcas_horizontais(Q, peso_trole, R_roda_max, n_rodas_lado, frac_lateral, frac_long):
    n_total = 2 * n_rodas_lado
    H_transv_roda = frac_lateral * (Q + peso_trole) / n_total   # surto (aceleracao trole)
    H_long_trilho = frac_long * R_roda_max * n_rodas_lado        # frenagem (rodas motoras)
    return H_transv_roda, H_long_trilho
```

---

## 3. Viga de rolamento — momento por carga móvel

```python
def _m_max_movel(P, d, L):
    # Momento maximo absoluto de 2 cargas iguais P espacadas d, vao L (biapoiada)
    if d < L:
        m2 = (2.0 * P / L) * (L / 2.0 - d / 4.0) ** 2
    else:
        m2 = 0.0
    return max(m2, P * L / 4.0)
```

Flexão vertical `Msdx = _m_max_movel(P, d, L)`; lateral do surto
`Msdy = _m_max_movel(Ht, d, L)`. **Surto atua no topo do trilho → só a mesa
superior resiste** (~metade das props):

```python
Wy_top, Zy_top = Wy / 2.0, Zy / 2.0
Mrdy = min(Zy_top, 1.5 * Wy_top) * fy / GA1
inter = Msdx / Mrdx + Msdy / Mrdy        # Mrdx pelo Anexo G (check)
```

---

## 4. ELS (flecha) e fadiga

```python
def limite_flecha_vertical(cap_kN, siderurgica):
    if siderurgica and cap_kN >= 200.0: return 1000.0   # L/1000
    if cap_kN >= 200.0: return 800.0                     # L/800
    return 600.0                                          # L/600
```

Flecha com carga **sem impacto** (`Pk = P/φ`). Horizontal L/400 (L/600
siderúrgica). Coluna: deslocamento no nível da viga ≤ Hvr/400. **Fadiga**
(Anexo K) sinalizada para pontes pesadas — não fabrica categoria de detalhe.

---

## 5. Pontos de conferência (FLAGS)

1. **φ, frac_lateral (~0,10), frac_long (~0,10)** — fabricante/NBR 8400.
2. Frenagem nas **rodas motoras**: reduzir frac_long por n_motoras/n_rodas.
3. Surto só na mesa superior (metade das props) — Fakury 4.4.2.
4. Fadiga: Anexo K sinalizado, não automatizado.

---

## 6. Onde revisar

| Assunto | Função | Item |
|---|---|---|
| Cargas de roda | `cargas_de_roda` | NBR 8800 cap. cargas |
| Horizontais | `forcas_horizontais` | NBR 8800 / 8400 |
| Momento móvel | `_m_max_movel` | mecânica |
| Viga rolamento | `verifica_viga_rolamento` | Anexo G + biaxial |
| Flecha | `limite_flecha_vertical` | ELS NBR 8800 |
