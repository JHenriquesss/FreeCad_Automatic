# Revisão — Contraventamento e barras tracionadas

Conferência do sênior. Barras tracionadas pela **NBR 8800:2008** (5.2):
contraventamento (diagonais redondas só-tração que levam o arrasto do vento
longitudinal à fundação), tirantes de terça (sag rods) e a barra da mão-francesa.

Código: `contraventamento.py`. Última atualização: 2026-07-06.

---

## 1. Barra tracionada (5.2)

```python
GA1 = 1.10 ; GA2 = 1.35
def tracao_barra_Rd(d, fy, fu, ct=1.0, k_rosca=0.75):
    Ag = math.pi * d ** 2 / 4.0
    An = k_rosca * Ag                       # area efetiva na rosca (~0,75 Ag)
    esc = Ag * fy / GA1                      # escoamento da secao bruta
    rup = ct * An * fu / GA2                 # ruptura da secao liquida
    return min(esc, rup), esc, rup
```

`Nt,Rd = min(Ag·fy/1,10 ; Ct·An·fu/1,35)`.

---

## 2. Força na diagonal e esbeltez (5.2.8)

```python
def n_diagonal(F_painel, dx, dy):
    L = math.hypot(dx, dy)
    cos_t = dx / L
    return F_painel / cos_t, L               # N = F_painel / cos(theta)

# esbeltez:
r_gir = d / 4.0                              # raio de giracao da secao cheia
lam = L / r_gir
esbeltez_ok = pretensionada or lam <= 300.0  # barra so-tracao pre-tensionada dispensa
```

---

## 3. Força de estabilização da mão-francesa (2%)

```python
def forca_estabilizacao_2pct(Msd, braco):
    return 0.02 * Msd / braco                # 2% da forca da mesa (Msd/braco)
```

---

## 4. Pontos de conferência (FLAGS)

1. **An = 0,75·Ag** na rosca ; **Ct = 1,0** (barra redonda).
2. **Esbeltez L/r ≤ 300** dispensada para barra só-tração **pré-tensionada**
   (esticador/turnbuckle) — reportado e sinalizado.
3. `F_painel` (arrasto por painel) vem de `Fa` do vento longitudinal — ver
   [REVISAO-VENTO.md](REVISAO-VENTO.md); fração por diagonal = arranjo (A CONFIRMAR).
4. Regra dos 2% para estabilização — confirmar aplicabilidade.

---

## 5. Onde revisar

| Assunto | Função | Item NBR 8800 |
|---|---|---|
| Nt,Rd | `tracao_barra_Rd` | 5.2 |
| Diagonal | `n_diagonal` | — |
| Esbeltez | `verifica_barra` | 5.2.8 |
| Estabilização 2% | `forca_estabilizacao_2pct` | — |
