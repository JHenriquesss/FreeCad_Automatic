# Revisão — Terças (formado a frio, NBR 14762)

Conferência do sênior. Terça de cobertura em perfil U enrijecido (Ue) pela
**NBR 14762:2010** (9.8 + Anexo F) + flambagem distorcional (FSM em
`distorcional_fsm.py`). Adoção do perfil mais leve por `tercas_iteracao.py`.

Código: `tercas_nbr14762.py`. Norma: NBR 14762 (`pesquisa/aço/`).
Última atualização: 2026-07-06.

> Propriedades do perfil = catálogo do fornecedor (**A CONFIRMAR**).

---

## 1. Flambagem local — módulo efetivo (MSE, 9.8.2.1)

`kl` da Tabela 13 (Ue) por interpolação dupla em ζ = bf/bw e μ = D/bw.

```python
def Wef_MSE(W, Wc, kl, bw, t, fy):
    Ml = kl * math.pi ** 2 * E / (12 * (1 - NU ** 2)) * (t / bw) ** 2 * Wc
    lp = math.sqrt(W * fy / Ml)
    Wef = W if lp <= 0.673 else W * (1 - 0.22 / lp) / lp
    return Wef, Ml, lp
```

`Mrd,local = Wef·fy/γ` (γ = 1,10).

---

## 2. Sucção — mesa comprimida livre (Anexo F)

```python
def fator_R_anexoF(bw_mm, secao="U", continua=False):   # Tabela F.1
    if continua:  return 0.70 if secao == "Z" else 0.60
    if bw_mm <= 165: return 0.70
    if bw_mm <= 216: return 0.65
    if bw_mm <= 292: return 0.50 if secao == "Z" else 0.40
    return None                                          # fora do escopo
# Mrd,succao = R · Wef · fy / γ
```

---

## 3. Distorcional (9.8.2.3)

Dispensa pela Tabela 14 (D/bw ≥ limite). Se não dispensa e há Mdist (da análise
de estabilidade elástica / FSM):

```python
def chi_distorcional(W, fy, Mdist):
    lam = math.sqrt(W * fy / Mdist)
    chi = 1.0 if lam <= 0.673 else (1 - 0.22 / lam) / lam
    return chi, lam
# Mrd,dist = chi · W · fy / γ ; entra no menor MRd
```

Se **não dispensa e sem Mdist** → **INCONCLUSIVO sob sucção** (não inventa).
`distorcional_fsm.py` fornece o Mdist pela Finite Strip Method (assinatura de
flambagem) quando disponível.

---

## 4. Cortante (9.8.3) e eixo fraco

```python
def cortante_Vrd(h, t, fy, kv=5.0):
    lam = h / t
    lp = 1.08 * math.sqrt(E * kv / fy) ; lr = 1.40 * math.sqrt(E * kv / fy)
    if lam <= lp:  return 0.6 * fy * h * t / GA
    if lam <= lr:  return 0.65 * t**2 * math.sqrt(kv*fy*E) / GA
    return (0.905 * E * kv * t**3 / h) / GA
```

Eixo fraco: `Wef,y` com redução de flambagem local da mesa (não usa Wy bruto —
seria contra a segurança sob sucção); método **aproximado**, sobrescrevível por
`perfil['Wefy']` (rigoroso).

---

## 5. Flexão oblíqua + ELU + ELS

Gravidade decompõe em `qx = vert·cosθ`, `qy = vert·senθ`; vento é **normal** ao
telhado (só qx). Interação `Msx/Mrdx + Msy/Mrdy ≤ 1`. Modelo estático auto-
selecionado: biapoiado (1/8, 1/2, 5/384) ou contínuo ≥3 vãos (1/10, 0,6, 2,6/384).

γg favorável = **0,90** (conservador p/ uplift; NBR 8681/critério do RT — a NBR
8800 Tab.1 permite 1,00, configurável).

ELS: flecha L/180 (gravidade), L/120 (vento sucção), com `Ief` (catálogo ou
fallback conservador `Ix·Wef/W`).

---

## 6. Pontos de conferência (FLAGS)

1. Propriedades do Ue (incl. Ief) — **catálogo**.
2. **Mrd,y aproximado** (ρ da mesa sobre Wy, k=4) — rigor pede flexão com
   gradiente e centroide efetivo no eixo y.
3. **Distorcional inconclusiva** sob sucção se não dispensa e sem Mdist.
4. **γg,fav = 0,90** (vs 1,00 da NBR 8800 Tab.1).
5. Tabelas 13/14 interpoladas — conferir contra o PDF.

---

## 7. Onde revisar

| Assunto | Função | Item NBR 14762 |
|---|---|---|
| kl (Tab.13) | `k_local` | Tabela 13 |
| Wef local | `Wef_MSE` | 9.8.2.1 |
| Sucção R | `fator_R_anexoF` | Anexo F / Tab. F.1 |
| Distorcional dispensa | `dispensa_distorcional` | Tabela 14 |
| Distorcional χ | `chi_distorcional` | 9.8.2.3 |
| Cortante | `cortante_Vrd` | 9.8.3 |
| Eixo fraco | `Wef_y_mesa` | 9.2.2 (MLE) |
| ELU/ELS | `verifica_terca` | 9.8 |
