# Revisão — Viga de baldrame / amarração entre sapatas

Conferência do sênior. Dimensiona a **viga de baldrame / amarração** entre as
sapatas em **concreto armado (NBR 6118:2014)**. Fecha a lacuna média #2 (ligação
entre fundações isoladas). Código: `viga_baldrame.py`. Criado 2026-07-08.

> **STATUS: 🆕 PENDENTE SÊNIOR** — módulo novo.

---

## 1. Dois papéis

1. **Baldrame** — viga sob a **parede de fechamento** (alvenaria) vencendo o vão
   entre sapatas → flexão (NBR 6118 17.2) + armadura mínima (17.3.5, `ρmin`).
2. **Amarração** — absorve a **reação horizontal da base** do pilar (empuxo do
   pórtico) como **tração axial**, aliviando o atrito/empuxo passivo da sapata.
   `As = N_d/f_yd`. A força de amarração é a **reação V da base do próprio
   envelope** (não um valor arbitrado).

Reaproveita as rotinas de concreto **já homologadas** em `fundacao_sapata`
(`_armadura_flexao`, `rho_min`, `detalha_barras`) — mesmo método da sapata.

---

## 2. Método (valores lidos do PDF NBR 6118)

- **Flexão:** `M_d = γf·cM·w·L²` (cM=1/8 biapoiada, 1/10 contínua); `w` = carga da
  parede + peso próprio (`25·b·h`, NBR 6118). `As` pelo bloco retangular 17.2.2
  (via `_armadura_flexao`), com verificação de domínio (`x/d`).
- **Amarração:** `As,tie = γf·N_tie/f_yd`, `f_yd = f_yk/1,15`; dividida nas 2 faces.
- **Armadura mínima:** `As,min = ρmin·b·h` (Tabela 17.3, piso **0,15 %**).
- **Composição:** `As,inf = max(As,flexão + As,tie/2 ; As,min)` ;
  `As,sup = max(As,tie/2 ; As,min)`. Barras por `detalha_barras`.
- **Detalhamento:** largura mínima **b ≥ 12 cm** (NBR 6118 **13.2.2**, verbatim:
  *"a seção transversal das vigas não pode apresentar largura menor que 12 cm"*);
  estribos `s_max = 0,6·d ≤ 300 mm` (**18.3.3.2**, para `Vd ≤ 0,67·VRd2`).
- `γf = 1,4` ; `fcd = fck/1,4` ; `fyd = fyk/1,15`.

---

## 3. Código (verbatim)

```python
GAMMA_C_CONC = 25.0 ; GF = 1.4 ; B_MIN = 0.12    # NBR 6118

w_self = GAMMA_C_CONC*b*h ; w = q_parede + w_self
M_d = GF * cM * w * L**2                          # cM=1/8 (biapoiada)
As_flex,x_d,z,ok_dom = fs._armadura_flexao(M_d,b,d,fck,fyk)   # 17.2.2

Nd_tie = GF*abs(N_amarracao) ; As_tie = Nd_tie/(fyk/1.15)     # tracao

As_min = fs.rho_min(fck/1000)*b*h                 # Tab.17.3
As_inf = max(As_flex + As_tie/2, As_min)
As_sup = max(As_tie/2, As_min)
s_estribo = min(0.6*d, 0.30)                      # 18.3.3.2
```

---

## 4. FLAGS / limites de escopo

1. **Carga da parede (`q_parede`)** = tipo/altura da alvenaria de fechamento —
   entrada do gate (0 se fechamento só em telha metálica leve). No galpão de
   referência (fechamento em telha) → só peso próprio + amarração → **As,min governa**.
2. **Força de amarração** = **reação horizontal V da base** no envelope (real, do
   modelo). Não usa regra empírica (ex. Alonso `Nd/20`); se o engenheiro preferir
   o mínimo de robustez, informa `N_amarracao` maior.
3. **Não** verifica cisalhamento (VRd2/VRd3) — assume `Vd ≤ 0,67·VRd2` (baldrame
   de baixa solicitação; estribo mínimo `0,6d`). Para baldrame muito carregado,
   FLAG para verificar o cortante.
4. **Viga de equilíbrio / alavanca** (sapata de divisa excêntrica) é **outro**
   elemento — fora deste escopo.
5. Modelo biapoiado entre sapatas (conservador para o momento positivo); a
   continuidade real reduz o vão de momento (`continua` = cM 1/10 opcional).

---

## 5. Onde revisar

| Assunto | Função | Item NBR 6118 |
|---|---|---|
| Flexão | `fs._armadura_flexao` | 17.2.2 |
| Armadura mínima | `fs.rho_min` | 17.3.5 / Tab.17.3 |
| Amarração (tração) | `verifica_baldrame` | mecânica (As=Nd/fyd) |
| Largura mínima | `verifica_baldrame` | 13.2.2 |
| Estribo s_max | `verifica_baldrame` | 18.3.3.2 |
| Detalhe de barras | `fs.detalha_barras` | 18.3 |

---

## 6. Não-regressão

`python viga_baldrame.py --selftest` → **PASSED** (M_d=35 kN·m p/ w=8 kN/m; As,tie
conferida; domínio; b<12 reprova; seção pequena sob M grande reprova). Orquestrador:
`N_amarracao` auto = **max|V| da base no envelope** (ref: 32,9 kN do
C2_uplift_W2), `vao` = bay; `gate7-baldrame.txt`, item **11b** no consolidado.
Ref 20×10 (fechamento telha, `q_parede=0`): baldrame 20×40, As,min governa
(1,20 cm² → 2Φ10), amarração 1,06 cm². **APROVADA**. Aditivo: só roda com
`params["baldrame"]`. Aguarda revisão.
