# Revisão — Fundação profunda (estaca + bloco de coroamento)

Conferência do sênior. Fecha a **última lacuna grande**: fundação profunda —
capacidade de carga da **estaca** pelo método **Aoki-Velloso (1975)** a partir do
SPT (NBR 6122) e o **bloco de coroamento** em concreto armado (bielas-e-tirantes,
NBR 6118). Código: `estaca_profunda.py`. Criado 2026-07-08.

> **STATUS: 🆕 PENDENTE SÊNIOR** — módulo novo, escolha de sítio (opt-in).

---

## 1. Capacidade da estaca — Aoki-Velloso (1975)

```
R_ult = R_ponta + R_lateral
R_ponta   = (K·N_p / F1) · A_ponta
R_lateral = Σ_camadas (α·K·N_l / F2) · U · Δz
P_adm = R_ult / FS         (NBR 6122: FS=2,0 semi-empírico sem prova de carga)
```

`K` [kPa] e `α` [%] por tipo de solo = **Tabela 12.6**; `F1`, `F2` por tipo de
estaca = **Tabela 12.7**. Ambas **lidas do PDF** (Veloso & Lopes 2012 / Aoki-Velloso
1975, renderizadas como imagem — o texto OCR estava corrompido). `N` limitado a
**50** (Veloso & Lopes p.279). `U = π·D` (perímetro), `A_ponta = π·D²/4`.

### Tabela 12.6 (verbatim) — K [kPa = kgf/cm²×100], α [%]

| solo | K | α | solo | K | α |
|---|---|---|---|---|---|
| areia | 1000 | 1,4 | silte argiloarenoso | 250 | 3,0 |
| areia siltosa | 800 | 2,0 | silte argiloso | 230 | 3,4 |
| areia siltoargilosa | 700 | 2,4 | argila arenosa | 350 | 2,4 |
| areia argilossiltosa | 500 | 2,8 | argila arenossiltosa | 300 | 2,8 |
| areia argilosa | 600 | 3,0 | argila siltoarenosa | 330 | 3,0 |
| silte arenoso | 550 | 2,2 | argila siltosa | 220 | 4,0 |
| silte arenoargiloso | 450 | 2,8 | argila | 200 | 6,0 |
| silte | 400 | 3,0 | | | |

### Tabela 12.7 (verbatim) — F1, F2

| estaca | F1 | F2 |
|---|---|---|
| Franki | 2,5 | 5,0 |
| Metálica | 1,75 | 3,5 |
| Pré-moldada de concreto | 1,75 | 3,5 |
| Escavada | 3,0 | 6,0 |
| Raiz / hélice / ômega | 2,0 | 4,0 |

### Décourt-Quaresma (1978) — cross-check (Tab.12.12 / 12.13, verbatim)

2º método independente, para conferir o Aoki-Velloso:
```
q_ponta = C·N_p          (C em tf/m², ×10 → kPa)   ; R_ponta = q_ponta·A_ponta
r_lateral = (N_méd/3 + 1)·10  kPa  (3 ≤ N ≤ 50, independe do solo)
R_ult = R_ponta + R_lateral      ;  P_adm = R_ult / FS
```
**Tab.12.12 C [tf/m²]:** argila 12 · silte argiloso 20 · silte arenoso 25 · areia 40.
**Tab.12.13 (= N/3+1):** N≤3→2 · 6→3 · 9→4 · 12→5 · N≥15→6 tf/m². N_méd = média
ponderada de N ao longo do fuste embutido. Os 15 solos de Aoki são mapeados nos 4
grupos de Décourt (`_grupo_decourt`). No exemplo, Décourt dá R_ult 20 % **abaixo**
do Aoki (banda típica de dispersão entre métodos — os dois entram no relatório).

---

## 2. Número de estacas + bloco de coroamento

- **n estacas** = `⌈(N_pilar + peso_bloco) / P_adm⌉`.
- **Bloco rígido** (NBR 6118 22.3 admite bielas para blocos rígidos) por
  **bielas-e-tirantes** (modelo de Blévot), por **equilíbrio** (não um coeficiente
  memorizado): a biela vai do **quarto do pilar** (nó a `a_pilar/4` do eixo) até a
  **estaca** (a `espaçamento/2` do eixo); o componente horizontal é o tirante.

```
braço = espaçamento/2 − a_pilar/4
T = (N_pilar/n) · braço / d          (d = altura útil do bloco)
As = T / f_yd                        (f_yd = f_yk/1,15)
```

Implementado para blocos **simétricos de 2 ou 4 estacas**. Reaproveita o concreto
de `fundacao_sapata` (`rho_min`).

### Tração / arranque (uplift) — NBR 6122

Para o galpão, a combinação que governa a base é de **uplift** (sucção do vento) →
o pilar **arranca**, tracionando a estaca. À tração **só o atrito lateral resiste**
(a ponta não trabalha): `P_adm,tração = R_lateral / FS_tração` (FS_tração=2,0). O
orquestrador injeta `N_uplift` = maior reação **negativa** (tração) da base no
envelope e verifica `N_uplift/n ≤ P_adm,tração`.

---

## 3. FLAGS / limites de escopo

1. **Perfil de SPT** (tipo de solo + N por camada) = **sondagem do sítio** — entrada
   A CONFIRMAR. O método escala direto no N e no tipo de solo.
2. **FS = 2,0** (NBR 6122, método semi-empírico **sem prova de carga**) — valor
   global clássico, **configurável** (`FS`). A NBR 6122:2022 admite abordagem por
   fatores parciais; o engenheiro confirma o critério adotado. **A CONFIRMAR.**
3. **Décourt-Quaresma** implementado como **cross-check** (Tab.12.12/12.13 lidas do
   PDF). Resta a **2ª versão (α/β, Décourt 1996)** — trabalho futuro.
4. **Bloco**: tirante (22.3.3) + **biela comprimida** (22.3.2) implementados —
   `σ_pilar ≤ fcd1=0,85·αv2·fcd` (nó CCC) e `σ_estaca ≤ fcd3=0,72·αv2·fcd` (nó CCT),
   `αv2=1−fck/250`, `σ=Força/(A·sen²θ)`, ângulo `0,57 ≤ tanθ ≤ 2` (22.3.1). Bloco
   **rígido** (tanθ≥0,57) → **punção dispensada** (trabalha por bielas); flexível →
   FLAG verificar punção. Resta a **ancoragem** do tirante sobre a estaca.
5. **Tração/arranque (uplift)** implementado (atrito lateral / FS_tração). Restam
   **atrito negativo, efeito de grupo** (eficiência) e recalque do grupo — governam
   em solos moles / grupos densos; verificar à parte.
6. Só roda com `params["estaca"]` (escolha deliberada de fundação profunda); a
   referência 20×10 permanece em **sapata** (rasa).

---

## 4. Onde revisar

| Assunto | Função | Fonte |
|---|---|---|
| Capacidade Aoki-Velloso | `capacidade_aoki_velloso` | Veloso & Lopes 12.4.2 / Tab.12.6-12.7 |
| P_adm (FS) | idem | NBR 6122 |
| Número de estacas | `n_estacas` | — |
| Bloco (tirante) | `bloco_coroamento` | NBR 6118 22.3 (bielas) / Blévot |

---

## 5. Não-regressão

`python estaca_profunda.py --selftest` → **PASSED**. Exemplo (perfil argila/areia
siltosa/areia, estaca pré-moldada D30 L10): `R_ponta=1009,8` + `R_lateral=589,7` →
`R_ult=1599,5 kN`, `P_adm=799,8 kN`. N limite 50 conferido; tirante do bloco 2
estacas conferido por equilíbrio. Orquestrador: `N_pilar` = max|N| da base no
envelope; `gate7-estaca.txt`, item **11c** no consolidado; **só roda com
`params["estaca"]`** → referência (sapata) inalterada. Aguarda revisão.
