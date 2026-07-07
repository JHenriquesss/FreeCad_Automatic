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
telhado (só qx). Interação flexão `Msx/Mrdx + Msy/Mrdy ≤ 1`. Modelo estático auto-
selecionado: biapoiado (1/8, 1/2, 5/384) ou contínuo ≥3 vãos (1/10, 0,6, 2,6/384).

**9.8.4 — momento + cortante combinados** (alma sem enrijecedores transversais):

```python
mv = inter ** 2 + okv ** 2        # (Msd/Mrd)^2 + (Vsd/Vrd)^2 <= 1,0
ok = (inter <= 1.0 and okv <= 1.0 and mv <= 1.0
      and not (uplift and dist_inconclusivo))
```

Usa `inter` (utilização de flexão biaxial) como termo de momento — conservador
na flexão oblíqua.

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
6. ~~Interação M+V (9.8.4)~~ — ✅ adicionada nesta rodada (ver §8.1).

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
| M+V combinados | `verifica_terca` (`mv`) | 9.8.4 |
| Eixo fraco | `Wef_y_mesa` | 9.2.2 (MLE) |

---

## 8. Resposta ao parecer do sênior (rodada 1 — 2026-07-06)

Parecer conferido contra o texto autêntico da NBR 14762:2010 (PDF em
`pesquisa/aço/`). O parecer foi **elogioso e sem achado acionável**, mas a
auditoria própria (regra: verificar método na norma, não aceitar aval de cara)
encontrou **uma lacuna que o parecer não viu**.

### 8.1 — Faltava a interação M+V (9.8.4) — ADICIONADO

**Achado próprio (não apontado pelo parecer). CORRIGIDO.**

NBR 14762 **9.8.4** (pág. 56 do PDF), literal:
> "Para barras **sem enrijecedores transversais de alma**, o momento fletor
> solicitante de cálculo e a força cortante solicitante de cálculo na mesma
> seção devem satisfazer: **(Msd/Mrd)² + (Vsd/Vrd)² ≤ 1,0**"

A terça tem alma sem enrijecedores → a interação circular é obrigatória. O código
verificava flexão (`inter ≤ 1`) e cortante (`uV ≤ 1`) **separadamente**, mas não
a combinação. Adicionado `mv = inter² + uV² ≤ 1,0`. Ver §5.
Impacto: terça adotada (Ue 200×75×25×2,65) passa com `mv = 0,955² + 0,116² =
0,925 ≤ 1,0` — **sem regressão**, mesmo perfil selecionado.

### 8.2 — Confirmações verificadas contra o PDF (o parecer abençoou; conferi)

- **Cortante 9.8.3** — três domínios exatos (pág. 55): `0,6·fy·h·t` /
  `0,65·t²·√(kv·fy·E)` / `0,905·E·kv·t³/h`, com λp=1,08√(Ekv/fy),
  λr=1,40√(Ekv/fy), γ=1,10, kv=5 (alma sem enrijec., 9.8.3). ✅
- Winter local/distorcional (transição 0,673, `(1−0,22/λ)/λ`) ✅
- Anexo F (R por bw: 165/216/292 mm) ✅ · MSE 9.8.2.1 ✅ · interação flexão ✅

### 8.3 — Notas do parecer (nomenclatura / premissas) — mantidas

- `qx`/`qy` vs `Mx`/`My`: nomenclatura de eixos; matemática fecha (qx gera o
  momento no eixo forte). Mantida convenção do código (documentada na §5).
- γg,fav = 0,90: premissa conservadora do RT (NBR 8800 Tab.1 permite 1,00),
  configurável. Mantida como default. Ver FLAG 4.

### 8.4 — Não-regressão

Selftest OK · iteração: Ue 200×75×25×2,65 adotada (inter 0,95; mv 0,925; flecha
vento 12,7 mm) · galpão 20×10: coluna 0,67 / viga 0,93 inalteradas. Aguarda
re-revisão.

---

## 9. Homologação (rodada 2 — 2026-07-06)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 14762:2010.**

Sênior homologou a correção da §8.1 (interação M+V 9.8.4) e a implementação geral:
MSE local (9.8.2.1), Anexo F (sucção), distorcional inconclusiva sob uplift,
cortante 3 domínios (9.8.3), flexão oblíqua, γg,fav=0,90. Sem achado remanescente.

**Integração na otimização (pergunta do sênior):** a verificação M+V **já entra
automaticamente** na iteração de catálogo. `tercas_iteracao.avalia()` faz
`ok = all(c["OK"] for c in res["casos"].values())`, e `mv ≤ 1,0` já compõe o
`OK` de cada caso (§5). Logo `tercas_iteracao` descarta perfis que falhem no
cisalhamento combinado — não é só validador de etapa final. Nenhuma ação extra.

Módulos `tercas_nbr14762.py` + `tercas_iteracao.py` liberados.
| ELU/ELS | `verifica_terca` | 9.8 |
