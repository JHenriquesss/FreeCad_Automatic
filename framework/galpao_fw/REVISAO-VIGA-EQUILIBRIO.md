# Revisão — Viga de equilíbrio de divisa sobre estacas (variante profunda)

Novo módulo `viga_equilibrio.py`: variante **PROFUNDA** (estaca) da fundação de
divisa. Quando o pilar está na divisa do lote **e** a fundação é profunda, o grupo
de estacas não pode ser centrado sob o pilar (a divisa impede); o bloco fica
excêntrico e uma **viga de equilíbrio** (viga alavanca) o liga a um bloco interno.
Fecha o backlog "viga de equilíbrio de divisa excêntrica (estaca)". Fase 6.18.
Criado 2026-07-13.

> **STATUS: ✅ HOMOLOGADO — 3 CORRIGIDOS + pele adicionada** (2026-07-13). Erro de
> estática no momento (M=R'·e → **P·e**) + cisalhamento + peso próprio; 2ª rodada
> homologou e adicionou armadura de pele (h>60cm). Ver §Parecer. SI (m, kN). PT.

## Mecânica (corpo rígido — a MESMA já validada em `sapata_divisa`)

```
R' = P_divisa · l / (l − e)          reação amplificada no bloco de divisa
Delta_P = R' − P_divisa              acréscimo -> ALIVIA o pilar interno (praxe 50%)
M_viga = P_divisa · e                momento na viga (tração na face SUPERIOR) [ver §Parecer]
V_viga = Delta_P                     cortante CONSTANTE ao longo do vão (l − e)
```
> Corrigido do parecer: `M = P·e` (NÃO `R'·e`). Prova por corte no centroide do grupo:
> à direita do corte só atua `P_divisa` no braço `e` → `M = P·e`; pelo outro lado
> `Delta_P·(l−e) = (R'−P)(l−e) = P·l − P(l−e) = P·e`. Idênticos. `R'·e` superestimava
> por `R'/P = l/(l−e)`.
`l` = vão da viga (entre eixos dos pilares); `e` = excentricidade do eixo do pilar
ao centroide do grupo de estacas. **Não é norma nova** — é a estática de alavanca
de Alonso/Velloso & Lopes, já validada contra o exemplo trabalhado no
`sapata_divisa._selftest` (P=1400, e=0,79, l=5,5 → R=1635 kN).

## O que muda frente à sapata de divisa (variante rasa, já existente)

| | `sapata_divisa` (rasa) | `viga_equilibrio` (profunda) |
|---|---|---|
| Fundação de divisa | sapata excêntrica | **bloco sobre estacas** |
| Dimensiona | B×L da sapata (σ_solo) | **nº de estacas** = ⌈R'/P_adm⌉ |
| Capacidade | tensão admissível do solo | **P_adm da estaca** (sondagem, `estaca_profunda`) |
| Viga | alavanca (tração superior) | equilíbrio (tração superior) — **igual** |
| Alívio interno | 50% ΔP | 50% ΔP — **igual** |

## O que revisar

1. **Estática da alavanca** — `R'=P·l/(l−e)`, `ΔP`, `M=R'·e`, `V=ΔP`, alívio 50%.
   Idêntica ao `sapata_divisa` (homologado no item 34/D45).
2. **Grupo de estacas** — `n = estaca_profunda.n_estacas(R', P_adm)["n"]`;
   carga/estaca ≤ P_adm. `P_adm` vem da sondagem (Ask-Do-Not-Invent).
3. **Excentricidade `e`** — default geométrico `excentricidade_estimada`:
   2 estacas ⊥ à divisa, `x_centroide = D/2 + folga_borda + s/2`,
   `e = x_centroide − dist_divisa` (`s=3D` praxe). **Arranjo A CONFIRMAR** (depende
   do diâmetro/arranjo real); `e` pode ser passado explicitamente.
4. **Viga de equilíbrio** — RC tracionada na face superior; armadura por
   `fundacao_sapata._armadura_flexao` (NBR 6118, já homologado); itera `h` (l/7)
   até passar; `As_min` por `rho_min`.
5. **Wiring (`rodar_galpao`)** — o gate de divisa **ramifica**: com `params["estaca"]`
   → `viga_equilibrio` (usa a `P_adm` da estaca já calculada); senão →
   `sapata_divisa` (rasa). Corrigido shadowing de aliases (`est`→`est_res`,
   `ve`→`veq`) que colidiam com locais de `rodar`. Runtime end-to-end confirmado
   (`res["divisa"]["tipo"]` ∈ {estaca, sapata}).

## Parecer do sênior (2026-07-13) — 3 correções (estática conferida do zero)

### 1 — Momento fletor `M = P·e`, não `R'·e` — 🔴 ERRO GRAVE, CORRIGIDO

Conferi a estática por FBD independente (corte no centroide do grupo): à direita do
corte a única força é `P_divisa` no braço `e` → **`M = P·e`**. Pelo lado interno,
`Delta_P·(l−e) = P·e` (idêntico). O código usava `R'·e`, que **superestimava** o
momento por `l/(l−e)`. No selftest (P=1400, e=0,75, l=5,5): era `1621·0,75=1216` kN·m,
agora `1400·0,75=1050` kN·m → menos armadura de flexão injustificada. **Sênior correto.**
Corrigido `viga_equilibrio.py` (`M_viga = P_divisa * e`), relatório e selftest.

### 2 — Cisalhamento obrigatório (NBR 6118 §17.4) — 🔴 OMISSÃO, ADICIONADO

`V_viga = Delta_P` é **constante** ao longo do vão. Faltava verificar a viga ao
cortante. Adicionada verificação via `viga_baldrame._verifica_cortante` (biela `VRd2`
+ estribo mínimo `VRd3`, Modelo I θ=45°) com `Vd = 1,4·Delta_P`. A iteração de altura
agora cresce `h` até passar **flexão E biela**; espaçamento de estribo por §18.3.3.2
(`s ≤ 0,6d≤30cm` ou `0,3d≤20cm` se `Vd>0,67 VRd2`). Saídas novas: `V_d_kN`, `VRd2_kN`,
`VRd3_min_kN`, `u_biela`, `s_estribo_cm`, `ok_cortante`. No selftest a viga subiu de
~79 cm para 102 cm de altura (governada pela biela).

### 3 — Peso próprio na contagem de estacas — 🟡 ADICIONADO

Bloco+viga são peças robustas; peso próprio (praxe Alonso ~5% da reação) entra na
contagem: `n = ⌈1,05·R'/P_adm⌉` via `estaca_profunda.n_estacas(..., peso_bloco=0,05·R')`.
Aplicado ao bloco de divisa e ao interno. `FATOR_PP=1,05` constante nomeada, documentada
como praxe (FLAG — refinar com peso real de bloco+viga no detalhamento).

### 4 — Armadura de pele (NBR 6118 §17.3.5.2.3) — 🟡 ADICIONADO (2ª rodada)

O sênior perguntou pela pele: a nova verificação de cisalhamento elevou a viga a
102 cm (>60 cm), disparando a exigência. Verbatim (PDF 6118 pág 132/§17.3.5.2.3):
*"A mínima armadura lateral deve ser 0,10% Ac,alma em cada face da alma... espaçamento
não maior que 20 cm... não sendo necessária armadura superior a 5 cm²/m por face. Em
vigas com altura igual ou inferior a 60 cm, pode ser dispensada."* Implementado:
`As_pele/face = min(0,10%·b·h, 5 cm²/m·h)`, `s≤20 cm`, só quando `h>0,60 m`; senão
`aplica=False`. Saída `viga.pele`. Ex. viga 40×102: **4,08 cm²/face**.

### Confirmados sem alteração
- Estática de `R'` e `Delta_P`: OK. Alívio 50% no interno (viga calculada p/ 100% de
  `Delta_P`): OK (parecer endossa). Excentricidade geométrica `e`: OK.

## Cobertura de teste (fase 6.18)

`tests/test_fase618_viga_equilibrio.py` — 11 testes: reação amplificada (fórmula do
braço); e maior amplifica mais; nº de estacas cobre R'; alívio 50% no interno; viga
passa à flexão; **M = P·e e não R'·e (estática)**; **cisalhamento V=Delta_P (biela
VRd2 + estribo)**; **peso próprio ~5% na contagem de estacas**; excentricidade
geométrica; **armadura de pele h>60cm (0,10% Ac,alma/face)**; **pele dispensada
h≤60cm**; relatório PT; wiring escolhe a variante estaca. **13 testes.**

## Escopo (FLAGs — Ask-Do-Not-Invent)

- `P_adm` da estaca (sondagem), cargas reais dos pilares (envelope do pórtico) e o
  arranjo/excentricidade do grupo na divisa = **entradas**; bloqueiam se não
  informados. Detalhamento (ancoragem, estribos da viga) = executivo.
