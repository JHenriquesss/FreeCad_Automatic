# Revisão — Fundação (sapata isolada)

Documento para revisão do engenheiro sênior. Descreve o **método** de
dimensionamento da sapata, com as **citações exatas da NBR 6118:2014**
(PDF em `pesquisa/aço/`), a lógica do **envelope de combinações**, e as
**limitações/pendências** deixadas explícitas no memorial.

> CONCEITUAL — o framework calcula e dimensiona; o engenheiro responsável
> revisa e assina (ART). Nada aqui é projeto executivo.

Código: `framework/galpao_fw/fundacao_sapata.py`
Fluxo: `rodar_galpao.py` Gate 7 (`_casos_base_envelope` → `fs.dimensiona_sapata_env`).

Última atualização: 2026-07-06.

---

## 1. Escopo

Sapata **isolada** sob a reação de base de um pilar de galpão (N, V, M),
dividida em duas partes por rigor de método:

- **Parte A** — geotecnia/estabilidade (estática pura, independe de norma de
  concreto).
- **Parte B** — concreto armado, **método extraído da NBR 6118:2014**.

Fora de escopo (marcado PENDENTE): bloco sobre estacas/tubulão, sapata
flexível (punção), detalhamento executivo da armadura.

---

## 2. Parte A — geotecnia / estabilidade

Entrada: reação (N, V, M) por combinação; `sigma_solo_adm` (**input da
sondagem** — não é inventado, bloqueia o cálculo se não informado); `mu`,
`coesão`, peso específico do solo/concreto.

### 2.1 Tensão no solo (flexão composta)

Excentricidade `e = |M| / N`.

- **Núcleo** (`e ≤ L/6`) — contato total:
  `σ_max,min = N/(B·L) · (1 ± 6e/L)`
- **Borda** (`e > L/6`) — levantamento parcial, diagrama triangular:
  comprimento de contato `x = 3·(L/2 − e)`; `σ_max = 2N/(B·x)`.

Critério: `σ_max ≤ σ_solo,adm`.

### 2.2 Estabilidade

N estabilizante inclui o **peso próprio** da sapata + pedestal + reaterro.

- **Tombamento**: `FS = M_estab / M_tomb`, com
  `M_estab = N_tot · L/2` e `M_tomb = |V|·h_total + |M|`. Mínimo usual **1,5**.
- **Deslizamento**: `FS = (N_tot·μ + c·A) / |V|`. Mínimo usual **1,5**.

> Os fatores 1,5 são prática usual (ELU geotécnico) — **confirmar** com o
> critério adotado no projeto. Ficam como parâmetro do caso.

---

## 3. Parte B — concreto armado (NBR 6118:2014)

Todas as referências abaixo foram extraídas do PDF da norma.

### 3.1 Rigidez — item 22.6.1

Sapata **rígida** se, nas duas direções:
`h ≥ (a − a_p)/3` (a = dimensão da sapata; a_p = dimensão do pilar).

O código **aumenta h** até satisfazer a rigidez (só ajuda a Parte A). Sendo
rígida, o item **22.6.2.2** dispensa a verificação de **punção** (a sapata
fica dentro do cone) — resta a **compressão diagonal** (19.5.3.1).

> Se a geometria não puder ser rígida, o memorial emite FLAG exigindo punção
> (19.5) e flexão não-uniforme (22.6.4.1.3) — **PENDENTE**.

### 3.2 Flexão — itens 22.6.3 (modelo de flexão) + 17.2.2 (bloco retangular)

Momento na **face do pilar**, balanço `c = (a − a_p)/2`, pressão de cálculo
(conservadora) `σ_d` uniforme sobre o balanço:
`M_d = σ_d · largura · c²/2` (uma direção por vez).

Armadura por **bloco retangular** (17.2.2, fck ≤ 50 MPa → `λ = 0,8`,
`α_c = 0,85`):

```
μ    = M_d / (b·d²·α_c·f_cd)
x/d  = (1 − √(1 − 2μ)) / λ          (limite de ductilidade x/d ≤ 0,45, 14.6.4.3)
z    = d·(1 − 0,5·λ·x/d)
A_s  = M_d / (f_yd·z)
```

Altura útil `d = h − cobrimento − φ`. Armadura mínima `A_s,min = 0,15%·b·h`
(17.3.5.2 — **confirmar** para o fck adotado).

### 3.3 Compressão diagonal — item 19.5.3.1

No **perímetro do pilar** `u0 = 2·(a_p,L + a_p,B)`:

```
τ_Sd  = F_d/(u0·d) + K·M_d/(Wp0·d)         (parcela de momento, 19.5.2.2)
τ_Rd2 = 0,27·α_v·f_cd ,   α_v = (1 − f_ck/250)  [f_ck em MPa]
```

`K` da **Tabela 19.2** (função de C1/C2, interpolado). `Wp0 = C1²/2 + C1·C2`
(módulo plástico do contorno do pilar). Critério `τ_Sd ≤ τ_Rd2`.

---

## 4. Envelope de combinações (por elemento)

**Fecha o gap** de usar uma única combinação. Cada verificação pega a
combinação ELU que a governa:

- **bearing (σ_solo)** → combinação de **N máximo** (gravitacional);
- **tombamento / deslizamento** → **N mínimo** com **M/V máximo** (uplift);
- **flexão** → maior `A_s` entre as combinações (adota o maior);
- **compressão diagonal** → maior `τ_Sd`.

Código: `_casos_base_envelope()` devolve todas as combinações ELU na base
(cruzamento W1/W2, com/sem ponte); `dimensiona_sapata_env()` adota a **menor
geometria da escada que passa TODAS as combinações**, e o memorial imprime a
combinação governante de cada verificação.

Exemplo (nf982, 20×10, ponte 100 kN): bearing governado por `C4_ponte`
(N = +205 kN, o caso que a abordagem antiga de “só max |M|” perdia, pois lá
N ≈ 1,3 kN); tombamento por `C2_uplift`. Sapata adotada 2,0 × 2,5 × 0,75 m,
rígida, util 0,27.

---

## 4b. Quantitativo (concreto + aço)

`quantitativo(rA, rB, n_sapatas)` — por sapata × nº de sapatas
(`2 pilares × nº de pórticos`):

- **Concreto** (m³): `B·L·h` do bloco + pedestal.
- **Aço** (kg): `(A_s,L·(B−0,10) + A_s,B·(L−0,10)) · 7850` — A_s é área total
  por largura (já integra a quantidade de barras); comprimento aproximado das
  barras. Indicador `taxa` em kg/m³.

Aparece no memorial `gate7-fundacao.txt` e no DXF (nota sob o detalhe da base).
Ex. nf982: 10 sapatas, 38,0 m³ de concreto, 865 kg de aço (taxa ~23 kg/m³).

> Aproximação de **anteprojeto** (não substitui o detalhamento executivo, que
> define bitolas, espaçamentos, ganchos e traspasses).

## 5. Limitações / pendências (FLAGS no memorial)

1. `sigma_solo,adm` e parâmetros do solo (μ, coesão, γ) — **relatório de
   sondagem** (geotecnia). Bloqueia se não informado.
2. Sapata **flexível** exige punção (19.5) — PENDENTE (o código força rígida).
3. `A_s,min` = 0,15% (17.3.5.2) — confirmar para o fck.
4. **Detalhamento/ancoragem** da armadura (gancho face a face 22.6.4.1.1;
   arranque 22.6.4.1.2) — projeto executivo.
5. Fatores de segurança 1,5 (tombamento/deslizamento) — confirmar critério.

---

## 6. Onde revisar no código

| Assunto | Função | Item NBR |
|---|---|---|
| Tensão no solo | `tensoes_solo` | flexão composta |
| Estabilidade | `estabilidade` | — |
| Escolha da geometria | `dimensiona_sapata_env` | — |
| Rigidez | `dimensiona_sapata_B` (bloco rigidez) | 22.6.1 / 22.6.2.2 |
| Flexão / armadura | `_armadura_flexao` | 22.6.3 / 17.2.2 / 14.6.4.3 |
| Compressão diagonal | `dimensiona_sapata_B` (bloco compr_diag) | 19.5.3.1 / Tab. 19.2 |
| Combinações na base | `rodar_galpao._casos_base_envelope` | `_combos_elu` |
