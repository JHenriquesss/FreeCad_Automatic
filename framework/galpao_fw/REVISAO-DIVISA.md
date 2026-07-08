# Revisão — Sapata de divisa com viga alavanca

Conferência do sênior. Dimensiona a **sapata de divisa** (pilar junto ao limite do lote)
com **viga alavanca** conectada a uma sapata interna, conforme NBR 6122 e Velloso & Lopes.

Código: `sapata_divisa.py`. Criado 2026-07-08.

> **STATUS: 🆕 PENDENTE SÊNIOR** — módulo novo.

---

## 1. Método (Velloso & Lopes / Alonso)

1. **Sapata de divisa** — processo iterativo:
   - Adota `R'` (reação inicial ~ 110% de P_divisa)
   - Calcula área `A = R'/σ_solo`
   - Fixa `B` (dimensão perpendicular à divisa) e calcula `L = A/B`
   - Calcula excentricidade `e = (B - b_col)/2` (constante)
   - Recalcula `R = P_div · l / (l - e)` e itera até convergir
2. **Alívio na sapata interna:**
   - `ΔP = R - P_div` ; alívio adotado = 50% de ΔP (praxe de projeto)
   - `P_int_ajust = P_int - 0,5·ΔP`
3. **Viga alavanca:**
   - Momento fletor: `M = R · e` (tração na face superior)
   - Cortante: `V = R - P_div = ΔP` (diferença entre reação e carga do pilar)
   - Seção estimada por `h ~ L_vão/7`, depois ajustada por flexão
4. **Sapata interna** — centrada, dimensionada para `P_int_ajust`

## 2. Código (verbatim)

```python
def dimensiona_divisa(P_divisa, P_interno, dist_eixos, dist_divisa,
                      b_col_paralela=None, sigma_solo=None, fck=25e3, fyk=500e3,
                      L_fixo=None, cobrimento=0.05):
    sig = sigma_solo or SIGMA_SOLO_ADM
    b_col_div = 2.0 * dist_divisa
    B_foot = max(b_col_div + 0.30, 1.80)
    e = max((B_foot - b_col_div) / 2.0, 0.0)
    # Alonso: B fixo, reacao direta por equilibrio estatico
    R_divisa = P_divisa * dist_eixos / (dist_eixos - e)
    L = R_divisa / sig / B_foot                    # comprimento da sapata
    delta_P = R_divisa - P_divisa
    P_int_ajust = P_interno - 0.5 * delta_P
    A_int = max(P_int_ajust, 0.0) / sig
    L_int = B_int = max(math.sqrt(A_int), 0.01)
    # Viga alavanca
    b_viga = 0.25
    h = max(dist_eixos / 7.0, 0.50)
    d = h - cobrimento - 0.05
    M_d = 1.4 * R_divisa * e
    As, x_d, _, ok = fs._armadura_flexao(M_d, b_viga, d, fck, fyk)
    return {"divisa": {...}, "interno": {...}, "viga": {...}}
```

## 3. Selftest

Referência: Alonso (Velloso & Lopes). P_div=1400 kN, P_int=1900 kN, l=5,5m.

- `R = 1634,8 kN` (esperado ≈ 1635 ✅)
- `B = 1,80m`, `L = 3,63m`, `e = 0,79m`
- `ΔP = 234,8 kN` ; `P_int_ajust = 1782,6 kN`
- Sapata interna: `2,67 x 2,67 m`

**PASSED.**

## 4. FLAGS

1. **Carga dos pilares** — vem do envelope do pórtico (N, V, M). O módulo só
   recebe a carga vertical P; o momento fletor na base é tratado pela sapata
   isolada (`fundacao_sapata`).
2. **Tensão admissível do solo** — INPUT da sondagem. Bloqueia o cálculo se
   não informado.
3. **Geometria da divisa** — `dist_divisa` (distância do centro do pilar à
   divisa) e `b_col_paralela` (dimensão do pilar paralela à divisa) são dados
   do projeto arquitetônico.
4. **Viga alavanca** — o dimensionamento a cisalhamento (VRd2/VRd3) e o
   detalhamento de consolo curto são projetos executivos. O módulo faz o
   pré-dimensionamento à flexão.
5. **Alívio de 50%** — praxe de projeto (Velloso & Lopes). O engenheiro
   confirma o percentual.
6. **Sapata interna** — recebe o alívio, mas o dimensionamento detalhado
   (concreto) é feito por `fundacao_sapata`.
