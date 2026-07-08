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

---

## 3. FLAGS / limites de escopo

1. **Perfil de SPT** (tipo de solo + N por camada) = **sondagem do sítio** — entrada
   A CONFIRMAR. O método escala direto no N e no tipo de solo.
2. **FS = 2,0** (NBR 6122, método semi-empírico **sem prova de carga**) — valor
   global clássico, **configurável** (`FS`). A NBR 6122:2022 admite abordagem por
   fatores parciais; o engenheiro confirma o critério adotado. **A CONFIRMAR.**
3. **Décourt-Quaresma** como 2º método (cross-check) = **trabalho futuro** — a
   tabela de C (Tab.12.12) não foi lida com nitidez suficiente no PDF; **não** foram
   fabricados valores (zero-erro).
4. **Bloco**: entrega o **tirante** (armadura principal). A **biela comprimida**
   (tensão ≤ limite NBR 6118), a **punção** do bloco e a ancoragem do tirante ficam
   **fora deste escopo** — FLAG para o projeto do bloco.
5. **Atrito negativo, tração/arranque, efeito de grupo** (eficiência) e recalque do
   grupo **não** tratados — governam em solos moles / estacas tracionadas (o uplift
   do galpão pode tracionar a estaca: verificar à parte).
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
