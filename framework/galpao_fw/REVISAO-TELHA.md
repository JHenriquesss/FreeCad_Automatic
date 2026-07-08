# Revisão — Telha de cobertura (vão × carga)

Conferência do sênior. Verifica a **telha** de cobertura vencendo o **vão entre
terças** (espaçamento das terças) pela **NBR 14762** (perfil formado a frio),
sob gravidade (G+Q) e **sucção local de borda/canto** (vento §8). Fecha o par com
a lacuna do Cpe médio: agora a sucção local tem um elemento que a resiste.

Código: `telha_cobertura.py`. Criado 2026-07-08.

> **STATUS: 🆕 PENDENTE SÊNIOR** — módulo novo.

---

## 1. Modelo

Telha = viga de **1 m de largura** apoiada nas terças. Método idêntico ao das
terças (reaproveita `E=200e6 kN/m²`, `γ=1,10`, limites de flecha L/180 e L/120):

- **ELU (flexão, NBR 14762 9.8):** `M_Sd ≤ M_Rd = Wef·fy/γ`.
- **ELS (flecha):** `δ ≤ L/180` (gravidade) e `δ ≤ L/120` (sucção de vento).
- **Vão máximo** (tabela vão×carga): inverte ELU e ELS e toma o menor.

Continuidade sobre as terças (coef. clássicos de carga uniforme):

| esquema | coef. M | coef. flecha |
|---|---|---|
| simples (1 vão) | 1/8 | 5/384 |
| 2 vãos | 1/8 (apoio) | 2,6/384 |
| contínua (3+ vãos) | 1/10 | 2,6/384 |

---

## 2. Cargas / combinações

Faixa de 1 m → carga distribuída `w = pressão·1 m` [kN/m]. Combinações (mesmos
coeficientes das terças, NBR 8800 Tab.1 / NBR 8681):

- **Gravidade:** `1,25·G + 1,50·Q` (G = peso da telha do catálogo + `G_extra`;
  Q = sobrecarga de cobertura = **0,25 kN/m²**, default do projeto).
- **Sucção:** `1,40·W − 0,90·G` (W = sucção **local** do vento §8; G favorável
  reduz o arranque, γ_g,fav=0,90 conservador, NBR 8681).

O ELU toma o **pior** dos dois. Para telha leve (G≈0,06 kN/m²) sob sucção local
de canto (−2,2 kN/m²), a **sucção governa** de longe.

---

## 3. Código (verbatim)

```python
E = 200e6 ; GA = 1.10   # NBR 14762

def m_rd(Wef_cm3_m, fy_MPa):                       # M_Rd = Wef*fy/gamma
    return (Wef_cm3_m*1e-6) * (fy_MPa*1e3) / GA

def flecha(w_kN_m, L, Ief_cm4_m, cD):              # cD*w*L^4/(E*I)
    return cD * w_kN_m * L**4 / (E * Ief_cm4_m*1e-8)

# ELU: w_grav = 1,25G+1,50Q ; w_upl = max(1,40W - 0,90G, 0) ; M = cM*w*L^2
# ELS: delta_grav <= L/180 ; delta_vento <= L/120 (cargas caracteristicas)
# vao_max: L_elu = sqrt(M_Rd/(cM*w)) ; L_els = ((E*I)/(cD*w*lim))^(1/3) ; min
```

---

## 4. FLAGS / limites de escopo

1. **Propriedades da telha (Wef, Ief, peso) = CATÁLOGO do fabricante** — não há
   seção normativa que as fixe; entram como parâmetro **A CONFIRMAR**. O exemplo
   `TELHA_EXEMPLO` (trapezoidal 40/0,65: Wef=7,5 cm³/m, Ief=18 cm⁴/m) é
   **ILUSTRATIVO**, não normativo. `Wef`/`Ief` já são propriedades **efetivas**
   (o catálogo publica valores de serviço); o módulo não recalcula largura efetiva.
2. **Não dimensiona o fixador** (parafuso auto-atarraxante telha→terça) — esse é
   do fabricante; o módulo entrega a telha entre apoios. A sucção de arranque do
   fixador vem de vento §8 (`sucao_local_fixacao`).
3. **Continuidade** é entrada (n de vãos) — default `simples` (conservador).
4. **Flambagem local do banzo comprimido sob sucção** (mesa larga da telha): a
   sucção comprime a mesa **inferior** (não enrijecida) — coberto de forma
   implícita pelo `Wef` de catálogo, que já é efetivo. FLAG para o engenheiro
   confirmar que o `Wef` fornecido corresponde ao sentido de sucção.

---

## 5. Onde revisar

| Assunto | Função | Item NBR |
|---|---|---|
| Momento resistente | `m_rd` | 14762 9.8 |
| Flecha | `flecha` / `verifica_telha` | 14762 (ELS) |
| Vão máximo | `vao_max` | inversão ELU/ELS |
| Combinações | `verifica_telha` | 8800 Tab.1 / 8681 |
| Sucção local | (vento §8) | 6123 Tab.4/5 |

---

## 6. Não-regressão

`python telha_cobertura.py --selftest` → **PASSED**. Ref 20×10 (vão=1,68 m =
√((10/2)²+0,5²)/3, W_sucao=−2,203 kN/m² auto do vento §8): sucção governa o ELU
(util 0,557), flecha OK, **vão máximo 2,187 m** (governa ELS vento L/120).
Orquestrador roda limpo; `gate7-telha.txt` gerado (item "6b. TELHA" no consolidado).
Aditivo: só roda com `params["telha"]`; ausência não afeta nada. Aguarda revisão.
